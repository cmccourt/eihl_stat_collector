from datetime import datetime
from typing import Protocol


class Website(Protocol):

    def get_list_of_matches(self, url: str = None, start_date: datetime = datetime.min,
                            end_date: datetime = datetime.max, teams: list or tuple = None):
        pass

    def get_match_info(self, match_date: datetime = None, teams: list or tuple = None):
        pass

    def extract_match_info(self, match_url: str):
        pass

    def extract_player_stats(self, match_url):
        pass

    def extract_team_stats(self, match_url):
        pass

    def get_championships(self):
        pass

    def get_match_stats_url(self, match_id):
        pass

    def get_gamecentre_url(self):
        pass

    def get_match_stats_url_from_main_game_page(self, url):
        pass

    def extract_match_stats(self, match_url):
        pass

    def get_team_stats_url_from_main_game_page(self, match_url):
        pass

    def get_all_gamecentre_urls(self):
        pass

    def get_list_of_matches_from_url(self, url: str = None,
                                     start_date: datetime = datetime.min,
                                     end_date: datetime = datetime.max, teams: list or tuple = None):
        pass
