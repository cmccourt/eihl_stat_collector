import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Tuple

from pypika import Query, Field, Table, MySQLQuery

from src.data_handlers.eihl_mysql import fetch_all_db_data, get_dup_records, insert_data
# from settings.settings import eihl_match_url
# from src.data_handlers.eihl_postgres import EIHLPostgresHandler
from src.match import update_db_match_score, get_db_matches, update_matches, insert_matches
from src.player_stats import insert_players_stats_to_db
from src.team_stats import update_match_team_stats
from src.web_scraping.eihl_website_scraping import EIHLWebsite
from src.web_scraping.website import Website

website: Website = EIHLWebsite()


@dataclass(init=True)
class CMDOption:
    help: str or None
    action: Callable
    params: Tuple = field(default=())


def display_help():
    print("Help\n")
    for option in Options:
        print(f"{option.name}: {option.value.help}")


def enter_date(fmt: str = "%d/%m/%Y"):
    while True:
        date_input = input("Enter date -> ")
        try:
            return datetime.strptime(date_input, fmt)
        except ValueError:
            # TODO find a way to display the format parameter in error message
            print("Invalid format! Format must be DD/MM/YY. Try again.")


def get_data_range() -> tuple[datetime, datetime]:
    while True:
        start_date = enter_date()
        end_date = enter_date()
        if start_date <= end_date:
            break
        print("Start date after end_date. Try again.")
    return start_date, end_date


def refresh_db():
    refresh_championships()
    insert_new_matches()
    update_matches(website)
    update_match_team_stats()
    insert_players_stats_to_db()


def refresh_championships():
    db_champs = fetch_all_db_data(table='championship', columns=[Field("eihl_web_id"), Field("name")])
    eihl_web_champs = website.get_championships()
    if eihl_web_champs == db_champs:
        print(f"All championship options are stored in the database")
    else:
        champ_diff = [x for x in eihl_web_champs if x not in db_champs]
        # for champ in champ_diff:
        #     champ_schedule_url = get_gamecentre_url(season_id=champ.get("eihl_web_id", None))
        #     start_dt, end_dt = get_start_end_dates_from_gamecentre(champ_schedule_url)
        #     champ["start_date"] = start_dt
        #     champ["end_date"] = end_dt
        for champ in champ_diff:
            try:
                if len(get_dup_records(params=champ, table="championship")) == 0:
                    insert_data("championship", champ)
            except Exception:
                traceback.print_exc()
            else:
                print("Championship has been inserted!")


def insert_new_matches(start_date: datetime = datetime.min, end_date: datetime = datetime.max,
                       teams: list | tuple | None = None):
    if teams is None:
        insert_matches(website, start_date, end_date)
    else:
        insert_matches(website, start_date, end_date, teams)



def update_recent_data():
    refresh_championships()
    match_query = MySQLQuery.from_("match").select("*")

    matches = fetch_all_db_data(
        str(match_query.where((Field("home_score").isnull()) | (Field("away_score").isnull()))))
    if len(matches) == 0:
        print("There are no matches to update!")
        return

    for match in matches:
        match_info = website.get_match_info(match)
        update_db_match_score(match_info)

    insert_matches(website)

    match_table = Table("match")
    update_empty_team_stats(match_table, match_query)

    update_empty_player_stats(match_query, match_table)


def update_empty_player_stats(match_query, match_table):
    player_stats_table = Table("match_player_stats")
    player_sub_query = Query() \
        .from_(match_table) \
        .select(match_table.match_id) \
        .left_join(player_stats_table) \
        .on(match_table.match_id == player_stats_table.match_id) \
        .groupby(match_table.match_id, player_stats_table.goals, player_stats_table.shutouts,
                 match_table.home_score, match_table.away_score) \
        .having(
        ((player_stats_table.goals.isnull()) & (player_stats_table.shutouts.isnull()) |
         (player_stats_table.goals == 0) & (player_stats_table.shutouts == 0)) |
        (match_table.home_score.isnull()) | (match_table.away_score.isnull()))
    miss_player_stat_query = str(match_query.where(Field("match_id").isin(player_sub_query)))
    missing_player_stat_games = fetch_all_db_data(miss_player_stat_query)
    # missing_player_stat_games = db_handler.fetch_all_data( """SELECT * FROM `match` WHERE match_id IN (SELECT
    # m.match_id FROM `match` m LEFT JOIN match_player_stats mps ON mps.match_id = m.match_id GROUP BY
    # m.match_id, mps.goals, mps.shutouts, m.home_score, m.away_score HAVING (mps.goals=0 AND mps.shutouts=0) OR
    # m.home_score IS NULL or m.away_score IS NULL)""")
    insert_players_stats_to_db(website, matches=missing_player_stat_games)


def insert_player_stats(start_date=None, end_date=None):
    if start_date is None:
        start_date = enter_date()
    if end_date is None:
        end_date = enter_date()
    matches = get_db_matches(start_date=start_date, end_date=end_date)
    insert_players_stats_to_db(website, matches)


def insert_team_match_stats(start_date=None, end_date=None):
    if start_date is None:
        start_date = enter_date()
    if end_date is None:
        end_date = enter_date()
    matches = get_db_matches(start_date=start_date, end_date=end_date)
    update_match_team_stats(website, matches=matches)


def update_empty_team_stats(match_table, match_query):
    team_stats_table = Table("match_team_stats")

    team_sub_query = Query() \
        .from_(match_table) \
        .select(match_table.match_id) \
        .left_join(team_stats_table) \
        .on(match_table.match_id == team_stats_table.match_id) \
        .groupby(match_table.match_id, team_stats_table.shots, team_stats_table.saves,
                 match_table.home_score, match_table.away_score) \
        .having((team_stats_table.shots.isnull()) & (team_stats_table.saves.isnull()) |
                (team_stats_table.shots == 0) | (team_stats_table.saves == 0) |
                (match_table.home_score.isnull()) |
                (match_table.away_score.isnull()))
    missing_team_stat_games = fetch_all_db_data(
        str(match_query.where(Field("match_id").isin(team_sub_query))))
    # missing_team_stat_games = db_handler.fetch_all_data( """SELECT * FROM `match` WHERE match_id IN (SELECT
    # m.match_id FROM `match` m LEFT JOIN match_team_stats mts ON m.match_id = mts.match_id GROUP BY m.match_id,
    # mts.shots, mts.saves, m.home_score, m.away_score HAVING mts.shots=0 or mts.saves=0 OR m.home_score IS NULL
    # or m.away_score IS NULL)""")
    update_match_team_stats(website, matches=missing_team_stat_games)


class Options(Enum):
    UPDATE_PLAYER_MATCH_STATS = CMDOption("Update player's stats for a particular match",
                                          insert_player_stats, (datetime.today(), datetime.max))
    UPDATE_DB_MATCH = CMDOption("Update score for a particular match in the database",
                                lambda x: "This will be implemented in the future")
    UPDATE_TEAM_MATCH_STATS = CMDOption("Update team's stats for a particular match", insert_team_match_stats,
                                        (datetime.min, datetime.max)
                                        )
    UPDATE_CHAMPIONSHIPS = CMDOption("Update EIHL championships in the DB", refresh_championships,
                                     )
    UPDATE_MATCH_SCORES = CMDOption("Update DB with the latest EIHL matches", insert_new_matches,
                                    )
    REFRESH_DB = CMDOption("Update recent matches and stats", refresh_db)
    UPDATE_RECENT = CMDOption("Update recent matches and stats", update_recent_data)
    HELP = CMDOption("You know what how this function works you eejit!", display_help)
    EXIT = CMDOption("Exit the program", exit)


def main():
    """Main function that takes the user's input in the while loop
       and performs the function specified"""

    is_exit = False
    while not is_exit:
        # user_input = input("What would you like to do? ->")
        user_input = "UPDATE_RECENT"
        if user_input is None:
            continue
        try:
            if Options[user_input].value.params:
                Options[user_input].value.action(*Options[user_input].value.params)
            else:
                Options[user_input].value.action()
        except KeyError:
            print("This is an invalid option!")
        break


if __name__ == "__main__":
    main()
