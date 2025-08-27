import traceback
from datetime import datetime
from typing import Any, Sequence

from mysql.connector import connect, connection, IntegrityError, DatabaseError
from pypika import MySQLQuery, Field, Criterion
from sqlalchemy import create_engine

from settings.settings import mysql_db_config


class mysql_connection(object):
    """MySQL DB connection"""

    def __init__(self, db_config=None):
        if db_config is None:
            self.db_config = mysql_db_config
        self.db_conn: connection = None

    def __enter__(self):
        self.db_conn = connect(**self.db_config)
        self.db_engine = create_engine(
            f"mysql+pymysql://{self.db_config.get('un', '')}:{self.db_config.get('pw', '')}@"
            f"{self.db_config.get('host', '')}:{self.db_config.get('port', '')}/{self.db_config.get('db', '')}",
            echo=True)
        return self.db_conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is None:
            self.db_conn.commit()
        else:
            self.db_conn.rollback()
        self.db_conn.close()


match_player_stats_cols = {
    "Jersey": "jersey",
    "Player name": "player_name",
    "Position": "position",
    "G": "goals",
    "A": "assists",
    "PTS": "points",
    "PIM": "penalty_mins",
    "PPG": "power_play_goals",
    "SHG": "short_hand_goals",
    "+/-": "plus_minus",
    "SOG": "shots_on_goal",
    "S": "shots",
    "FOW": "face_offs_won",
    "FOL": "face_offs_lost",
    "W": "wins",
    "L": "losts",
    "SO": "shutouts",
    "SA": "shots_against",
    "GA": "goals_against",
    "MIN": "mins_played",
    "SVS%": "save_percentage",
    "BS": "blocked_shots",
    "TOI": "toi"
}
match_team_stats_cols = {
    "Shots": "shots",
    "Shots on goal": "shots_on_goal",
    "Shots efficiency": "shot_efficiency",
    "Power plays": "power_plays",
    "Power play efficiency": "power_play_efficiency",
    "Penalty minutes": "penalty_minutes",
    "Penalty kill efficiency": "penalty_kill_efficiency",
    "Saves": "saves",
    "Save percentage": "save_percentage",
    "Faceoffs won": "faceoffs_won"
}


def print_sql_query(db_conn, query, params):
    if db_conn:
        print(db_conn.mogrify(query, params))
    else:
        print("ERROR unable to print SQL! No DB connection available!\n")


def fetch_all_db_data(query: MySQLQuery | str = None, params: dict = None,
                      table: str = None, columns: list = None):
    try:
        if query is None:
            query = MySQLQuery.from_(table)
            query = query.select(*columns) if columns is not None else query.select("*")
        if not isinstance(query, str):
            query = str(query)
        with mysql_connection() as db_conn, db_conn.cursor(dictionary=True) as db_cur:
            db_cur.execute(query, params)
            result = db_cur.fetchall()
            return result
    except Exception:
        traceback.print_exc()


def execute_query(query, params=None):
    with mysql_connection() as db_conn, db_conn.cursor(dictionary=True) as db_cur:
        try:
            db_cur.execute(query, params)
        except IntegrityError:
            db_conn.rollback()
            raise
        except Exception:
            db_conn.rollback()
            traceback.print_exc()
            print(f"Query -> {query} \n Params -> {params}")
            # print_sql_query(query, params)
        else:
            db_conn.commit()


def insert_data(table_name: str, new_val_dict: dict):
    query = str(MySQLQuery.into(table_name).columns(list(new_val_dict.keys())).insert(list(new_val_dict.values())))
    try:
        # print(db_cur.mogrify(query, player_match_stats))
        execute_query(query)
    except IntegrityError:
        raise
    except DatabaseError:
        raise


def update_data(table_name: str, update_values: dict, where_clause: Criterion = None):
    try:
        new_query = MySQLQuery.update(table_name)
        for key in update_values:
            new_query = new_query.set(key, update_values[key])
        if where_clause:
            new_query = new_query.where(where_clause)
        else:
            for col in update_values:
                new_query = new_query.where(Field(col) == update_values[col])
        print(f"Updating existing stats data for Values: {update_values}")
        # print(db_cur.mogrify(query, player_match_stats))
        execute_query(str(new_query), update_values)
    except TypeError:
        traceback.print_exc()


def get_dup_records(params: dict = None, query=None, table: str = None,
                    where_clause: Criterion = None) -> Sequence[Any]:
    if params is None:
        params = {}
    if query is not None:
        records = fetch_all_db_data(query)
    else:
        dup_match_query = MySQLQuery.from_(table).select("*")
        if where_clause is not None:
            dup_match_query = dup_match_query.where(where_clause)
        for col, val in params.items():
            dup_match_query = dup_match_query.where(Field(col) == val)

        records = fetch_all_db_data(str(dup_match_query), params)
    return records


# TODO Create team season ID table in DB to hold team ID for each season
# TODO create team ID converter in data source handler
def get_db_season_ids(seasons: list[str] = None, year_from: int | datetime = None,
                      year_to: int | datetime = None):
    season_ids = None
    if seasons is None:
        # get all EIHL season ids to iterate through
        season_ids = fetch_all_db_data(MySQLQuery.from_("championship").select("eihl_web_id"))
    return season_ids
