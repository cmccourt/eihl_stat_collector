import re
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup


@dataclass()
class MatchInfo:
    match_date: datetime = field(default_factory=datetime)
    home_team: str = field(default=None)
    away_team: str = field(default=None)
    home_score: int = field(default=None)
    away_score: int = field(default=None)
    home_team_info: dict = field(default_factory=dict, kw_only=True)
    away_team_info: dict = field(default_factory=dict, kw_only=True)


def get_date_range_from_str_list(text: list | tuple):
    start_date = None
    end_date = None
    for dt_regex, dt_fmt in ((r"([0-9]{2}/[0-9]{2}/[0-9]{4})", '%d/%m/%Y'),
                             (r"([0-9]{2}\.[0-9]{2}\.[0-9]{4})", '%d.%m.%Y')):
        dates = re.findall(dt_regex, text)
        try:
            dates = sorted([datetime.strptime(x, dt_fmt) for x in dates])
            start_date = dates[0]
            end_date = dates[-1]
        except IndexError:
            continue
    return start_date, end_date


def extract_date_from_str(text: str, fmt: str) -> datetime | None:
    try:
        text_dt = datetime.strptime(text, fmt)
        return text_dt
    except ValueError:
        return None


def extract_float_from_str(str_value: str, float_regex=r"(\d+.\d+)(?=%)"):
    if not isinstance(str_value, str):
        return None

    if re.findall(float_regex, str_value):
        float_value = re.search(float_regex, str_value).group(1)
    else:
        float_value = str_value

    try:
        float_value = float(float_value)
    except ValueError:
        print(f"Float conversion failed. Value: {str_value}")
        float_value = None
    return float_value


def get_html_content(url: str) -> BeautifulSoup:
    response = requests.get(url)
    res_beaus = BeautifulSoup(response.content, 'html.parser')
    return res_beaus

