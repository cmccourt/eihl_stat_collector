from fastapi import APIRouter
from pypika import MySQLQuery, Field, Table

from backend.src.data_handlers.eihl_mysql import fetch_all_db_data

router = APIRouter()


@router.get("/team_stats/{team_stats_id}")
def team_stats(team_stats_id: int, match: int = None, team: str = None):
    stats_query = MySQLQuery.from_("match_team_stats").select("*").where(Field("match_team_stat_id") == team_stats_id)

    try:
        stats = fetch_all_db_data(stats_query)
        if len(stats) == 0:
            print(f"There are no stats for match_id {team_stats_id}!")
        if team is not None:
            stats = [x for x in stats if x["team_name"] == team]
            if len(stats) == 0:
                print(f"Team {team} does not have any stats for match_id {team_stats_id}!")
    except Exception:
        stats = []
    return stats


@router.get("/team_match_stats/{match_id}")
def team_match_stats(match_id: int, team: str = None):
    # match_table = Table("match")
    team_stats_table = Table("match_team_stats")
    match_query = MySQLQuery.from_(team_stats_table).select("*")
    # .join(match_table).on(match_table.match_id == team_stats_table.match_id)

    if team is not None:
        match_query = match_query.where((team_stats_table.match_id == match_id) & (Field("team_name") == team))
    else:
        match_query = match_query.where(team_stats_table.match_id == match_id)

    try:
        stats = fetch_all_db_data(match_query)
        if len(stats) == 0:
            print(f"The stats for match {match_id} does not exist!")
    except Exception:
        stats = []
    return stats
