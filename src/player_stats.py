import traceback
from queue import Queue
from threading import Thread

import pandas as pd
from mysql.connector import IntegrityError

from src.data_handlers.eihl_mysql import insert_data, match_player_stats_cols
from src.web_scraping.website import Website


def insert_player_stats_to_db(*player_match_stats: dict):
    for player_stats in player_match_stats:
        team_name = player_stats.get("team_name", None)
        player_name = player_stats.get("player_name", None)
        match_id = player_stats.get("match_id", None)
        # TODO find better solution to replace NaNs with Nones
        player_stats = {k: (v if not isinstance(v, float) or not pd.isna(v) else None)
                        for k, v in player_stats.items()}

        try:
            print(f"Match ID: {match_id}, team: {team_name}, player {player_name} stats to be inserted!")
            insert_data("match_player_stats", player_stats)
            print(f"Match ID: {match_id}, team: {team_name}, player {player_name} inserted successfully!")
        except IntegrityError:
            print(f"Match ID: {match_id}, team: {team_name}, player {player_name} already exists in DB")
        except Exception:
            traceback.print_exc()


def get_player_stats(website: Website, match=None, match_stats_url: str = None) -> list[dict]:
    player_stats = []
    match_stats: pd.DataFrame = website.extract_match_stats(match_stats_url)
    for team_name, team_stats in match_stats.items():
        team_stats = team_stats.rename(columns=match_player_stats_cols)
        try:
            team_stats["team_name"] = team_name
            team_stats["match_id"] = match.get("match_id", None)
            team_stat_dicts: dict = team_stats.to_dict('records')
            player_stats.append(team_stat_dicts)
        except AttributeError:
            traceback.print_exc()
    return player_stats


def player_stats_consumer(stat_queue, website: Website):
    print("Consumer: Running")
    while True:
        match_info = stat_queue.get(block=True)
        # match_info, match_url = stat_queue.get(block=True)
        if match_info is None:
            break
        match_url = match_info.get("match_url", None)
        match_url = website.get_match_stats_url(match_url)
        try:
            all_player_stats = get_player_stats(website, match_info, match_url)
            for team_player_stats in all_player_stats:
                insert_player_stats_to_db(*team_player_stats)
        except Exception:
            traceback.print_exc()
        finally:
            stat_queue.task_done()
    print('Consumer: Done')


def insert_players_stats_to_db(website, matches: list[dict], num_threads=5):
    matches_queue = Queue()
    for match in matches:
        matches_queue.put(match)
    # add_match_to_queue(matches_queue, matches, website)
    consumers = [Thread(target=player_stats_consumer, args=(matches_queue, website)) for _ in range(num_threads)]
    # TODO implement logging
    try:
        for consumer in consumers:
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            consumer.daemon = True
            consumer.start()
    except Exception:
        print("THREADING ERROR!")
    # producer = Thread(target=player_stats_producer, args=(matches_queue, matches))
    # producer.start()
    # producer.join()
    # for consumer in consumers:
    #     consumer.join()
    matches_queue.join()
    print("Player match stats insertion Successful!!!")
