import traceback
from datetime import datetime
from pprint import pprint
from queue import Queue
from threading import Thread

from mysql.connector import IntegrityError
from pypika import Field, Parameter, MySQLQuery

# TODO Create Protocol for DB handler
from src.data_handlers.eihl_mysql import fetch_all_db_data, get_dup_records, update_data, insert_data
from src.web_scraping.website import Website


def get_db_matches(teams: list[str] = None,
                   start_date: datetime = None, end_date: datetime = None):
    if not start_date:
        start_date = datetime.min
    if not end_date:
        end_date = datetime.max
    match_query = MySQLQuery.from_("match").select("*").where((Field("match_date").between(start_date, end_date)))
    if teams:
        match_query = match_query.where((Field("home_team").isin(teams)) | (Field("away_team").isin(teams)))

    matches = fetch_all_db_data(str(match_query))
    return matches


def update_db_match_score(match_info):
    dup_clause = ((Field("match_date") == match_info.get("match_date", None).strftime("%Y-%m-%d %H:%M:%S")) &
                  (Field("home_team") == match_info.get("home_team", None)) &
                  (Field("away_team") == match_info.get("away_team", None)))
    dup_records = get_dup_records(table="match", where_clause=dup_clause)

    if dup_records and \
            (dup_records[0].get("home_score", None) is None or dup_records[0].get("away_score", None) is None):
        update_data("match", match_info, where_clause=dup_clause)
        print(f"Match Successfully updated: {match_info}")
    else:
        print(f"ERROR cannot find {match_info} in DB")


def get_match_producer(url_queue, match_queue, website: Website):
    print("Producer: Running")
    while True:
        url = url_queue.get(block=True)
        if url is None:
            break
        try:
            matches = website.get_matches(url=url)
            for match in matches:
                match_queue.put(match)
        except Exception:
            traceback.print_exc()
        finally:
            url_queue.task_done()
    print('Producer: Done')


def get_match_consumer(match_queue, website: Website):
    print("Consumer: Running")
    while True:
        match = match_queue.get(block=True)
        if match is None or match == []:
            break
        try:
            insert_data("match", match)
        except IntegrityError:
            print(f"Match: {pprint(match)} already exists in DB")
        except Exception:
            traceback.print_exc()
        else:
            pprint(match)
        finally:
            match_queue.task_done()
    print('Consumer: Done')


def insert_matches(website, start_date: datetime = None, end_date: datetime = None,
                   teams: list | tuple = None, num_threads=5):
    # TODO change this function so it calls Website.get_matches
    # TODO create multi thread function to get matches
    gamecentre_urls = website.get_all_gamecentre_urls()
    url_queue = Queue()
    match_queue = Queue()
    for url in gamecentre_urls:
        url_queue.put(url)
    producers = [Thread(target=get_match_producer, args=(url_queue, match_queue, website)) for _ in range(num_threads)]
    # TODO implement logging
    try:
        for producer in producers:
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            producer.daemon = True
            producer.start()
    except Exception:
        print("PRODUCER THREADING ERROR!")
    url_queue.join()
    consumers = [Thread(target=get_match_consumer, args=(match_queue, website)) for _ in range(num_threads)]
    try:
        for consumer in consumers:
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            consumer.daemon = True
            consumer.start()
    except Exception:
        print("CONSUMER THREADING ERROR!")
    match_queue.join()
    print("All Matches inserted successfully!!!")


def update_matches(website, start_date: datetime = None, end_date: datetime = None,
                   teams: list | tuple = None):
    dup_clause = ((Field("match_date") == Parameter("%(match_date)s")) &
                  (Field("home_team") == Parameter("%(home_team)s")) &
                  (Field("away_team") == Parameter("%(away_team)s")))
    matches = website.get_matches(start_date=start_date, end_date=end_date, teams=teams)
    try:
        # for season in season_ids:
        #     season_id = season["eihl_web_id"]
        #     season_gamecentre_url = website.get_gamecentre_url(season_id, team_ids, month_ids)
        #     season_matches = website.get_list_of_matches(season_gamecentre_url)
        # update_match_scores(db_handler, season_matches)
        for match in matches:
            pprint(match)
            dup_records = get_dup_records(params=match, table="match", where_clause=dup_clause)
            if len(dup_records) == 1:
                update_data("match", match, where_clause=dup_clause)
            else:
                # TODO Implement logging for this scenario
                print(f"More than 1 duplicate for match: {match}")
    except Exception:
        traceback.print_exc()
