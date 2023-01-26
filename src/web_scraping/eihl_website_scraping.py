import re
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Callable

import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup

from settings.settings import eihl_schedule_url, match_team_stats_cols, eihl_match_url
from src.utils import get_date_format, extract_float_from_str, get_html_content


def extract_team_match_stats(match_html: str) -> dict:
    # find div class called container
    # Then find an H2 called Team Stats
    # Iterate through the stats and assign them to the right team
    match_html_content = get_html_content(match_html)
    home_team_stats = defaultdict()
    away_team_stats = defaultdict()

    html_container = match_html_content.findAll('div', attrs={'class': 'container'})[0]
    stats_html: bs4.Tag = html_container.find("div")
    test = stats_html.find("h2")
    if "TEAM STATS" in test.get_text().upper():
        stat_text = list(stats_html.get_text("|", strip=True).split("|"))
        if stat_text[0].lower() == "team stats":
            del stat_text[0]
        # We go backwards in the loop as the stat titles are below the numbers
        i = len(stat_text) - 1
        while i is not None:
            if i < 0:
                break
            stat = stat_text[i]
            if not any(char.isdigit() for char in stat):
                # TODO replace dependency to db columns
                db_col = match_team_stats_cols.get(stat_text[i], stat_text[i])
                # As we're going backwards the away stats will be before the home stats
                if match_team_stats_cols.get(stat_text[i - 1], None) is not None or \
                        match_team_stats_cols.get(stat_text[i - 2], None) is not None:
                    home_stat = 0.0
                    away_stat = 0.0
                    # Only go one level down to get next stat
                    i -= 1
                else:
                    away_stat = extract_float_from_str(stat_text[i - 1])
                    if away_stat is None or away_stat == "":
                        away_stat = 0.0

                    home_stat = extract_float_from_str(stat_text[i - 2])
                    if home_stat is None or home_stat == "":
                        home_stat = 0.0
                    # Go to next stat
                    i -= 3
                away_team_stats[db_col] = away_stat
                home_team_stats[db_col] = home_stat
            else:
                # Move to next stat
                i -= 1

    match_team_stats = {"home_team": home_team_stats, "away_team": away_team_stats}
    return match_team_stats


def get_eihl_championship_options(schedule_url: str = eihl_schedule_url):
    res_beaus = get_html_content(schedule_url)
    html_id_season = res_beaus.body.find(id="id_season")
    champ_list = []
    id_search = "id_season="
    for s_id in html_id_season.find_all("option"):
        champ_id = s_id.get("value")
        if not champ_id:
            continue
        try:
            champ_id = int(champ_id[champ_id.find(id_search) + len(id_search):])
            champ_list.append({"eihl_web_id": champ_id, "name": s_id.get_text()})
        except ValueError:
            print(traceback.print_exc())
        print(s_id)
    return champ_list


def get_eihl_web_match_id(match_row_html) -> int or None:
    a_tag = match_row_html.find("a")
    game_web_id = re.findall(r"(?<=/game/).*$", a_tag.get('href', None))[0]
    try:
        if game_web_id:
            return game_web_id
    except Exception:
        print(f"{game_web_id} is not a valid number")
        traceback.print_exc()
    return None


def get_match_html_tags(url: str) -> list[(bs4.Tag, datetime.date)]:
    res_beaus = get_html_content(url)

    html_content = res_beaus.find("body").find("main").find(class_="wrapper")
    html_content = html_content.find(class_="container-fluid text-center text-md-left")

    matches = []
    match_date = None
    for tag in html_content:
        game_date_text = tag.get_text()
        game_date = get_date_format(game_date_text, "%A %d.%m.%Y")
        if game_date is not None and match_date != game_date_text:
            match_date = game_date

        if tag.name == "div" and len(tag.find_all()) > 0:
            matches.append((tag, match_date))
    return matches


def get_matches(url: str, filt: Callable[[str], bool] = lambda x: True):
    res_beaus = get_html_content(url)

    html_content = res_beaus.find("body").find("main").find(class_="wrapper")
    html_content = html_content.find(class_="container-fluid text-center text-md-left")

    matches = []
    match_date = None
    for tag in html_content:
        game_date_text = tag.get_text()
        game_date = get_date_format(game_date_text, "%A %d.%m.%Y")
        if game_date is not None and match_date != game_date_text:
            match_date = game_date

        if tag.name == "div" and len(tag.find_all()) > 0:
            match_info = extract_match_info(tag, match_date)
            matches.append(match_info)
    return matches


def extract_match_info(tag, match_date=None):
    match_info = defaultdict()
    match_info["eihl_web_match_id"] = get_eihl_web_match_id(tag)
    match_details = [r.text.strip() for r in tag.contents]
    match_details = [x for x in match_details if x.lower() not in ("", "details")]

    match_info["match_date"] = match_date
    try:
        match_time = get_date_format(match_details[0], "%H:%M").time()
        match_info["match_date"] = datetime.combine(match_date, match_time)
    except AttributeError:
        # no time present. Created dummy placeholder
        match_details.insert(0, None)

    # EIHL website for older seasons have game numbers or match type between time and home team
    if str.isdigit(match_details[1]) or len(match_details) > 2:
        del match_details[1]
    match_details[1] = match_details[1].replace("\n", "").strip()
    match_details[1] = re.sub('  +', '\t', match_details[1])
    match_details[1] = (match_details[1].split("\t"))
    match_info["home_team"] = match_details[1][0]
    match_info["away_team"] = match_details[1][-1]
    # if match went to OT or SO then we need to separate that
    try:
        score = match_details[1][1].split(":")
    except IndexError:
        print(type(match_details[1]))
        traceback.print_exc()
        print(match_details)
    else:
        if score[0] != "-":
            match_info["home_score"] = int(score[0])
            # OT or SO could be in string
            try:
                away_score, match_type = score[1].split(" ")
            except ValueError:
                away_score = score[1]
                match_type = "R"
            match_info["away_score"] = int(away_score)
            match_info["match_win_type"] = match_type
        else:
            match_info["home_score"] = None
            match_info["away_score"] = None
            match_info["match_win_type"] = None
    return match_info


def get_match_player_stats(url: str) -> defaultdict[pd.DataFrame]:
    response = requests.get(url)
    res_beaus = BeautifulSoup(response.content, 'html.parser')
    html_container = res_beaus.find('div', attrs={'class': 'container'})
    # html_container: bs4.Tag = html_container.find("div")
    game_stats = defaultdict(pd.DataFrame)
    pg_header_regex = re.compile("(?<= -).players|(?<= -).goalies")
    all_player_headers = [x for x in html_container.find_all("h2")
                          if re.search(pg_header_regex, x.get_text()) is not None]
    head_index = 0
    player_head_len = len(all_player_headers)
    while head_index < player_head_len:
        next_head_tag = None
        table_tag = None
        player_stat_dtf = pd.DataFrame()
        team_name = all_player_headers[head_index].get_text().strip().split("-")[0]
        team_name = team_name.strip()
        # Working with 0 index notation
        if head_index + 1 < player_head_len:
            next_head_tag = all_player_headers[head_index + 1]
        for tag in all_player_headers[head_index].next_siblings:
            if next_head_tag is not None and tag is next_head_tag:
                break
            elif isinstance(tag, bs4.Tag):
                table_tag = tag.findChildren("table", limit=1)
                if table_tag is not None:
                    table_tag = tag
                    break
        # TODO Change if statement to try except
        if isinstance(table_tag, bs4.Tag):
            try:
                player_stat_dtf = pd.read_html(str(table_tag))[0]
            except ValueError:
                print(f"ERROR No tables found for: {table_tag}")
        game_stats[team_name] = pd.concat([game_stats[team_name], player_stat_dtf], ignore_index=False)
        head_index += 1
    return game_stats


def get_gamecentre_month_id(month_num: int = None) -> int:
    """

    Args:
        month_num: the month of the year in number form (e.g. January = 1, March = 3, October = 10 etc)

    Returns: month ID

    """
    if month_num is None:
        return 999
    elif month_num > 12:
        print(f"Month number {month_num} is Invalid")
    return month_num


# TODO finish function
def get_gamecentre_team_id(team_name: str = None):
    if team_name is None:
        return 0
    else:
        return team_name


def get_gamecentre_url(team_id: int, month_id: int, season_id: int, base_url: str = eihl_schedule_url) -> str:
    season_url = f"{base_url}?id_season={season_id}&id_team={team_id}&id_month={month_id}"
    return season_url


def get_eihl_match_url(match_id: int, base_url: str = eihl_match_url) -> str:
    match_url = f"{base_url}{match_id}/team-stats"
    return match_url


def get_match_stats(match_stats_url):
    print(f"\nNext match is {match_stats_url}\n")
    match_stats = get_match_player_stats(match_stats_url)
    # Check if the team score table came through
    if len(match_stats) > 4 and len(match_stats[0].columns) <= 4:
        del match_stats[0]
    return match_stats