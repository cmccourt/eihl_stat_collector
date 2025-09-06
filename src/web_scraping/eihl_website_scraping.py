import re
import traceback
from collections import defaultdict
from datetime import datetime
from io import StringIO
from typing import Any

import bs4
import pandas as pd
from pandas import DataFrame

# from src.data_handlers.eihl_mysql import EIHLMysqlHandler
# from settings.settings import eihl_schedule_url, eihl_match_url
from src.utils import extract_date_from_str, extract_float_from_str, get_html_content, get_date_range_from_str_list
from src.web_scraping.website import Website


class EIHLWebsite(Website):
    eihl_base_url = "https://www.eliteleague.co.uk/"
    eihl_team_url = f"{eihl_base_url}team/"
    eihl_schedule_url = f"{eihl_base_url}schedule"
    eihl_match_url = f"{eihl_base_url}game/"

    def_month_id = 999
    def_team_id = 0

    def get_championships(self, schedule_url: str = None):
        if schedule_url is None:
            schedule_url = self.eihl_schedule_url
        res_beaus = get_html_content(schedule_url)
        html_id_season = res_beaus.body.find(id="id_season")
        champ_list = []
        id_search = "id_season="
        for s_id in html_id_season.find_all("option"):
            champ_id = s_id.get("value")
            if not champ_id:
                continue
            champ_info = {}
            try:
                champ_info["eihl_web_id"] = int(champ_id[champ_id.find(id_search) + len(id_search):])
                champ_info["name"] = s_id.get_text()
                champ_schedule_url = self.get_gamecentre_url(season_id=champ_info["eihl_web_id"])
                start_dt, end_dt = self.get_start_end_dates_from_gamecentre(champ_schedule_url)
                champ_info["start_date"] = start_dt
                champ_info["end_date"] = end_dt
                champ_list.append(champ_info)
            except ValueError:
                print(traceback.print_exc())
        return champ_list

    def get_start_end_dates_from_gamecentre(self, schedule_url: str = None) -> tuple[
        datetime | None, datetime | None]:
        if schedule_url is None:
            schedule_url = self.eihl_schedule_url
        # Get container that holds matches
        res_beaus = get_html_content(schedule_url)
        html_content = res_beaus.find("body").find("main").find(class_="wrapper")
        html_content = html_content.find(class_="container-fluid text-center text-md-left")
        html_text: str = html_content.get_text(separator=",", strip=True)
        start_date, end_date = get_date_range_from_str_list(html_text)
        return start_date, end_date

    def extract_team_stats(self, match_html: str) -> dict:
        # find div class called container
        # Then find an H2 called Team Stats
        # Iterate through the stats and assign them to the right team
        match_html_content = get_html_content(match_html)
        home_team_stats = defaultdict()
        away_team_stats = defaultdict()

        html_container = match_html_content.findAll('div', attrs={'class': 'container'})[0]
        stats_html: bs4.Tag = html_container.find("div")
        # E.g. of values that match Regex: 20, 20.0, 20%, 20.06%
        stat_float_regex = r"(\d+(\.\d+)?%)|(\d+(\.\d+))|(\d+)"
        try:
            if stats_html.find("h2") is not None and "TEAM STATS" in stats_html.find("h2").get_text().upper():
                # Found the team stats section
                stat_list = list(stats_html.get_text("|", strip=True).split("|"))
                if stat_list[0].lower() == "team stats":
                    del stat_list[0]
                self.get_team_stats_from_list(away_team_stats, home_team_stats, stat_float_regex, stat_list)
        except AttributeError:
            traceback.print_exc()

        match_team_stats = {"home_team": home_team_stats, "away_team": away_team_stats}
        return match_team_stats

    def get_team_stats_from_list(self, away_team_stats, home_team_stats, stat_float_regex, stat_list):
        def assign_stat_to_team(header, team_stats, stats=None, stat_index=None, value=None):
            if stats is not None and stat_index is not None:
                try:
                    value = stats[stat_index]
                except IndexError:
                    value = None
            team_stats[header] = extract_float_from_str(value) or 0.0

        stat_list_len = len(stat_list)
        i = 0
        stat_header = None
        while i < stat_list_len:
            stat_value = stat_list[i]
            if not re.findall(stat_float_regex, stat_value):
                stat_header = stat_value
                # Add stats for category
                assign_stat_to_team(stat_value, home_team_stats, stat_list, i + 1)
                assign_stat_to_team(stat_value, away_team_stats, stat_list, i + 2)
            elif stat_header is None:
                # find the category this number belongs too
                next_header_index = next((j for j in range(i, stat_list_len)
                                          if not re.findall(stat_float_regex, stat_list[j])))
                stat_header = stat_list[next_header_index]
                assign_stat_to_team(stat_header, home_team_stats, value=stat_value)
                assign_stat_to_team(stat_header, away_team_stats, stat_list, i + 1)
                i = next_header_index + 1
                stat_header = None
                continue
            i += 1

    def get_eihl_web_match_id(self, url: str) -> int | None:
        game_web_id = re.findall(r"(?<=/game/).*$", url)
        try:
            game_web_id = game_web_id[0]
        except KeyError:
            print(f"{game_web_id} is not a valid number")
            traceback.print_exc()
            return None
        return game_web_id

    def extract_match_info(self, match_url: str) -> dict:
        match_info = defaultdict()
        res_beaus = get_html_content(match_url)
        html_content = res_beaus.find("body").find("main").find(class_="wrapper").find("article")
        match_divs = html_content.find("div")
        if match_divs is None:
            print(f"No match information was able for match URL: {match_url}")
            raise Exception

        match_info["eihl_web_match_id"] = self.get_eihl_web_match_id(match_url)
        try:
            match_dt_str = match_divs.find("div").get_text().strip()
            match_datetime = extract_date_from_str(match_dt_str, "%d %b %Y, %H:%M")
            if match_datetime is None:
                match_datetime = extract_date_from_str(match_dt_str, "%d %b %Y")
            match_info["match_date"] = match_datetime
        except (AttributeError, TypeError, KeyError):
            match_info["match_date"] = None

        match_overview_div = None
        for div in match_divs:
            try:
                img_tags = div.findAll("img")
            except AttributeError:
                continue
            # Div with team logos is the one with the scores
            if len(img_tags) > 0:
                match_overview_div = div
                break

        home_team_info = match_overview_div.find("div")
        match_info["home_team"] = " ".join([x for x in home_team_info.find("a").stripped_strings])

        match_score_div = home_team_info.find_next_sibling(lambda x: x.name == "div" and len(x.findAll("img")) == 0)
        match_ending_text = match_score_div.find("div").get_text().strip()
        match_info["match_win_type"] = None
        if match_ending_text == "end":
            match_info["match_win_type"] = "R"
        elif match_ending_text == "end after shootout":
            match_info["match_win_type"] = "SO"
        elif match_ending_text == "end after overtime":
            match_info["match_win_type"] = "OT"
        raw_score = match_score_div.findAll("div", attrs={'class': 'match-score'})[0].get_text()
        try:
            home_score, away_score = map(int, raw_score.split(":"))
        except (TypeError, ValueError):
            home_score, away_score = None, None
        match_info["home_score"] = home_score
        match_info["away_score"] = away_score

        away_team_info = match_score_div.find_next_sibling(lambda x: x.name == "div" and len(x.findAll("img")) == 0)
        match_info["away_team"] = " ".join([x for x in away_team_info.find("a").stripped_strings])
        return match_info

    def extract_matches_from_url(self, url):
        res_beaus = get_html_content(url)

        html_content = res_beaus.find("body").find("main").find(class_="wrapper")
        html_content = html_content.find(class_="container-fluid text-center text-md-left")

        gamecentre_date_fmt = "%A %d.%m.%Y"
        matches = []
        match_date = None
        for tag in html_content:
            tag_text = tag.get_text()
            game_date = extract_date_from_str(tag_text, gamecentre_date_fmt)
            if game_date is not None and match_date != tag_text:
                match_date = game_date
            if tag.name == "div" and len(tag.find_all()) > 0:
                # TODO should the data storage class handle column name conversions?
                match_info = self.extract_team_score_from_tag(tag)
                match_info["championship_id"] = self.get_season_id(url)
                match_info["match_date"] = match_date
                try:
                    match_a_tag = tag.find("a")
                    match_url = f"{self.eihl_base_url}{match_a_tag['href']}"
                except Exception:
                    match_url = None
                match_info["match_url"] = match_url
                try:
                    match_info["match_date"] = datetime.combine(match_date, match_info.pop("match_time"))
                except (AttributeError, TypeError, KeyError):
                    # No time present. Create time placeholder
                    match_info["match_date"] = match_date
                matches.append(match_info)
        return matches

    def get_matches(self, url: str = None,
                    start_date: datetime = datetime.min,
                    end_date: datetime = datetime.max, teams: list | tuple = None):

        matches = []
        if teams is None:
            teams = []
        if url is None:
            gamecentre_urls = self.get_all_gamecentre_urls()
            # matches = website.get_list_of_matches_from_url(start_date=start_date, end_date=end_date, teams=teams)
            for url in gamecentre_urls:
                url_matches = self.extract_matches_from_url(url)
                if url_matches:
                    matches.append(url_matches)
        else:
            matches = self.extract_matches_from_url(url)
        # TODO filter out matches on dates and teams
        matches = [x for x in matches if start_date <= x["match_date"] <= end_date]
        return matches

    def extract_team_score_from_tag(self, tag) -> dict:
        match_info = defaultdict()
        try:
            match_url = tag.find("a")['href']
        except Exception:
            match_url = None
        match_info["eihl_web_match_id"] = self.get_eihl_web_match_id(match_url)
        match_details = [r.text.strip() for r in tag.contents]
        match_details = [x for x in match_details if x.lower() not in ("", "details")]

        try:
            match_info["match_time"] = extract_date_from_str(match_details[0], "%H:%M").time()
        except AttributeError:
            # No time present. Create time placeholder
            match_info["match_time"] = None
            match_details.insert(0, None)

        # Older seasons on the EIHL website have game numbers or match type between time and home team
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

    def extract_player_stats(self, url: str) -> defaultdict[Any, DataFrame]:
        res_beaus = get_html_content(url)
        html_container = res_beaus.find('div', attrs={'class': 'container'})
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
            try:
                try:
                    player_stat_dtf = pd.read_html(StringIO(str(table_tag)))[0]
                except ValueError:
                    print(f"ERROR Stats are not available for match: {url}")

                game_stats[team_name] = pd.concat([game_stats[team_name], player_stat_dtf], ignore_index=False)
                try:
                    game_stats[team_name]["Position"] = game_stats[team_name]["Position"].fillna("GW")
                except KeyError:
                    pass
            # else:
            except AttributeError:
                print("Not a tag")
            head_index += 1
        return game_stats

    def get_gamecentre_month_id(self, month: str = None) -> int:
        """
        Args:
            month: the month of the year (e.g. January, Sep, March, Aug, October etc)
        Returns: month ID
        """
        if month is None:
            return self.def_month_id
        month_num = None
        month_fmt = "%b" if len(month) <= 4 else "%B"

        try:
            month_num = datetime.strptime(month, month_fmt).month
        except ValueError:
            print(f"Month {month} is Invalid")
        return month_num

    def get_champ_teams(self, schedule_url: str):
        res_beaus = get_html_content(schedule_url)
        html_id_season = res_beaus.body.find(id="id_team")
        champ_list = []
        id_search = "id_team="
        for s_id in html_id_season.find_all("option"):
            html_value = s_id.get("value")
            if not html_value:
                continue
            team_info = {}
            try:
                team_info["team_id"] = int(html_value[html_value.find(id_search) + len(id_search):])
            except ValueError:
                continue
            team_info["name"] = s_id.get_text()
            champ_list.append(team_info)

        return champ_list

    def get_gamecentre_team_id(self, team_name: str = None, season_id=None):
        if team_name is None:
            return self.def_team_id
        team_id = None
        if season_id is not None:
            html_content = get_html_content(self.eihl_schedule_url)
            team_dropdown_option = html_content.find("select", id="id_team")
            team_option = team_dropdown_option.find("option", text=team_name)
            try:
                team_id = int(re.findall(r"(?<=id_team=)+?(\d+)", team_option.get("value"))[0])
            except Exception:
                print(f"Cannot find ID for {team_name} for season: {season_id}")
        return team_id

    def get_all_gamecentre_urls(self, schedule_url: str = None):
        if schedule_url is None:
            schedule_url = self.eihl_schedule_url

        champs_list = self.get_championships()
        gc_urls = []
        for champ in champs_list:
            gc_urls.append(self.get_gamecentre_url(season_id=champ.get("eihl_web_id", None)))
        return gc_urls

    def get_season_id(self, url):
        try:
            season_id = re.search(r"(?<=id_season=)+?(\d+)", url).group(0)
            return int(season_id)
        except Exception:
            traceback.print_exc()
            print(f"Cannot find season ID in url: {url}")
        return None

    def get_match_stats_url(self, url):
        return f"{url}/stats"

    def get_team_stats_url(self, url):
        return f"{url}/team-stats"

    def get_gamecentre_url(self, season_id: int = None, team_id: int = None, month_id: int = None,
                           schedule_url: str = None) -> str:
        if schedule_url is None:
            schedule_url = self.eihl_schedule_url
        if team_id is None:
            team_id = self.def_team_id
        if month_id is None:
            month_id = self.def_month_id

        if season_id is not None:
            gc_url = f"{schedule_url}?id_season={season_id}&id_team={team_id}&id_month={month_id}"
        else:
            gc_url = f"{schedule_url}id_team={team_id}&id_month={month_id}"
        return gc_url

    def extract_match_stats(self, match_url):
        print(f"\nNext match is {match_url}\n")
        match_stats = self.extract_player_stats(match_url)
        # Check if the team score table came through
        if len(match_stats) > 4 and len(match_stats[0].columns) <= 4:
            del match_stats[0]
        return match_stats
