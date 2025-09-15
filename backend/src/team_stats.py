import traceback
from queue import Queue
from threading import Thread

from mysql.connector import IntegrityError

from backend.src.data_handlers.eihl_mysql import insert_data, match_team_stats_cols
from backend.src.web_scraping.website import Website


def team_stats_consumer(stat_queue, website: Website):
    print("Consumer: Running")
    while True:
        match_info = stat_queue.get(block=True)
        if match_info is None:
            break

        match_url = match_info.get("match_url", None)
        match_url = website.get_team_stats_url(match_url)

        try:
            match_stats = website.extract_team_stats(match_url)
            for team_name, team_stats in match_stats.items():
                # team_stats = team_stats.rename(columns=match_team_stats_cols)
                team_stats = {match_team_stats_cols.get(k, k): v for k, v in team_stats.items()}
                team_stats["team_name"] = match_info.get(team_name, None)
                team_stats["match_id"] = match_info.get("match_id", None)

                insert_team_match_stats_to_db(team_stats)
        except Exception:
            traceback.print_exc()
        finally:
            stat_queue.task_done()
    print('Consumer: Done')


def insert_team_match_stats_to_db(team_match_stats: dict):
    team_name = team_match_stats.get("team_name", None)
    match_id = team_match_stats.get("match_id", None)
    try:
        insert_data("match_team_stats", team_match_stats)
    except TypeError:
        traceback.print_exc()
    except IntegrityError:
        print(f"Match ID: {match_id} team: {team_name} already exists in DB")
    else:
        print(f"Match ID: {match_id} team: {team_name} stats inserted!")


def update_match_team_stats(website: Website, matches: list[dict], num_threads=5):
    matches_queue = Queue()

    for match in matches:
        matches_queue.put(match)

    consumers = [Thread(target=team_stats_consumer, args=(matches_queue, website)) for _ in range(num_threads)]
    # TODO implement logging
    try:
        for consumer in consumers:
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            consumer.daemon = True
            consumer.start()
    except Exception:
        print("THREADING ERROR!")
    matches_queue.join()
    print("Team match stats insertion Successful!!!")
