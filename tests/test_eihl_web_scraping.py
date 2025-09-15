from datetime import datetime

import pytest

from backend.src.web_scraping.eihl_website_scraping import extract_team_match_stats, get_eihl_championship_options, \
    get_start_end_dates_from_gamecentre, get_gamecentre_team_id, get_match_info_from_match_page
from settings.settings import eihl_schedule_url


@pytest.mark.parametrize("match_url,expected",
                         [("https://www.eliteleague.co.uk/game/4002-fif-she/team-stats",
                           {"home_team": {'Shots': 31.0, 'Shots on goal': 25.0,
                                          'Shots efficiency': 12.00,
                                          'Power plays': 3.0, 'Power play efficiency': 66.67,
                                          'Penalty minutes': 8.0,
                                          'Penalty kill efficiency': 66.67,
                                          'Saves': 37.0, 'Save percentage': 94.87,
                                          'Faceoffs won': 40.0},
                            "away_team": {'Shots': 61.0, 'Shots on goal': 39.0,
                                          'Shots efficiency': 5.13, 'Power plays': 3.0,
                                          'Power play efficiency': 33.33,
                                          'Penalty minutes': 8.0,
                                          'Penalty kill efficiency': 33.33, 'Saves': 22.0,
                                          'Save percentage': 88.00, 'Faceoffs won': 33.0}}),

                          ("https://www.eliteleague.co.uk/game/2154-lon-bas/team-stats",
                           {"home_team": {'Shots': 0, 'Shots on goal': 0,
                                          'Shots efficiency': 0,
                                          'Power plays': 0, 'Power play efficiency': 0,
                                          'Penalty minutes': 0,
                                          'Penalty kill efficiency': 0,
                                          'Saves': 0, 'Save percentage': 0,
                                          'Faceoffs won': 0},
                            "away_team": {'Shots': 0, 'Shots on goal': 0,
                                          'Shots efficiency': 0, 'Power plays': 0,
                                          'Power play efficiency': 0,
                                          'Penalty minutes': 0,
                                          'Penalty kill efficiency': 0, 'Saves': 0,
                                          'Save percentage': 0, 'Faceoffs won': 0}})])
def test_extract_team_match_stats(match_url, expected):
    match_team_stats = extract_team_match_stats(match_url)

    for team, stats in match_team_stats.items():
        if stats != expected[team]:
            pytest.fail(f"expected result: {expected[team]} \n"
                        f"Actual result: {stats}")


@pytest.mark.parametrize("test_url,expected_start,expected_end",
                         [("https://www.eliteleague.co.uk/schedule?id_season=36&id_team=0&id_month=999",
                           datetime(2022, 9, 10), datetime(2023, 4, 2)),
                          ("https://www.eliteleague.co.uk/schedule?id_season=22&id_team=0&id_month=999",
                           datetime(2003, 9, 12), datetime(2004, 3, 14)),
                          ("https://www.eliteleague.co.uk/schedule?id_season=10&id_team=0&id_month=999",
                           datetime(2017, 9, 2), datetime(2018, 3, 4))
                          ])
def test_get_start_end_dates_from_gamecentre(test_url, expected_start, expected_end):
    try:
        start_date, end_date = get_start_end_dates_from_gamecentre(test_url)
        assert start_date == expected_start and end_date == expected_end
    except Exception:
        pytest.fail()


def test_get_eihl_championship_options():
    url = eihl_schedule_url
    try:
        champ_options = get_eihl_championship_options(url)
    except Exception:
        pytest.fail()


@pytest.mark.parametrize("team_name,season_id,expected_id", [("Belfast Giants", 36, 310)])
def test_get_gamecentre_team_id(team_name, season_id, expected_id):
    try:
        team_id = get_gamecentre_team_id(team_name, season_id)
        assert team_id == expected_id
    except Exception:
        pytest.fail()


@pytest.mark.parametrize("match_url,expected", [("https://www.eliteleague.co.uk/game/4002-fif-she",
                                                 {'eihl_web_match_id': '4002-fif-she',
                                                  'match_time': datetime.time(19, 0),
                                                  'match_date': datetime.date(2023, 1, 25), 'home_team': 'Fife Flyers',
                                                  'match_win_type': 'R', 'home_score': 3, 'away_score': 2,
                                                  'away_team': 'Sheffield Steelers'}),
                                                ("https://www.eliteleague.co.uk/game/2154-lon-bas",
                                                 {'eihl_web_match_id': '2154-lon-bas',
                                                  'match_date': datetime.date(2004, 3, 2), 'home_team': 'London Racers',
                                                  'home_score': 4, 'away_score': 0, 'away_team': 'Basingstoke Bison'})
                                                ])
def test_get_info_from_match_webpage(match_url, expected):
    match_info = get_match_info_from_match_page(match_url)
    print(match_info)


def test_get_eihl_web_match_id():
    pass


def test_get_match_player_stats():
    pass
