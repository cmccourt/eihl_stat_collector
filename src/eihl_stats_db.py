from datetime import datetime

import psycopg2
import pandas as pd
import numpy as np
from psycopg2 import _psycopg, sql, extras
import pandas.io.sql as sqlio
from settings.settings import EIHLStatsDBConfig


def db_connection() -> _psycopg.connection:
    db_conn = None
    try:
        db_conn = psycopg2.connect(dbname=EIHLStatsDBConfig.db,
                                   user=EIHLStatsDBConfig.un,
                                   password=EIHLStatsDBConfig.pw,
                                   host=EIHLStatsDBConfig.hostname)
    except psycopg2.DatabaseError:
        print("ERROR connecting to EIHL Stats Database!!")
    return db_conn


def db_cursor(db_conn: _psycopg.connection) -> _psycopg.cursor:
    db_cur = None
    try:
        db_cur = db_conn.cursor(cursor_factory=extras.DictCursor)
    except psycopg2.Error:
        print("ERROR creating DB Cursor!")
    return db_cur


def insert_championship(champ: dict, cursor: _psycopg.cursor, db_conn: _psycopg.connection = None):
    cursor.execute("SELECT * FROM championship", db_conn)
    col_headers = [desc[0] for desc in cursor.description]
    # columns to exclude from comparison
    exclude_cols = ["champion_id", "start_date", "end_date"]

    champ_dtf = pd.DataFrame(data=cursor.fetchall(),
                             columns=col_headers)
    champ_dtf = champ_dtf.drop(exclude_cols, axis=1)

    champ_series = pd.DataFrame([champ], columns=col_headers)
    champ_series = champ_series.drop(exclude_cols, axis=1)
    champ_dtf["name"] = champ_dtf["name"].str.strip()
    champ_series["name"] = champ_series["name"].str.strip()
    # check datatypes for each column
    champ_dtf = champ_dtf.astype(champ_series.dtypes.to_dict())
    try:
        merged_dtfs = pd.merge(champ_dtf, champ_series, how='inner')
        if merged_dtfs.empty:
            insert_sql = sql.SQL("INSERT INTO championship ({}) VALUES ({})").format(
                sql.SQL(", ").join(map(sql.Identifier, champ)),
                sql.SQL(", ").join(map(sql.Placeholder, champ))
            )
            cursor.execute(insert_sql, champ)
    except Exception as e:
        print(e)
    else:
        db_conn.commit()

    print("MATCH has been inserted!")


def insert_match(match: dict, cursor: _psycopg.cursor, db_conn: _psycopg.connection = None):
    cursor.execute("SELECT * FROM match", db_conn)
    col_headers = [desc[0] for desc in cursor.description]
    # columns to exclude from comparison
    exclude_cols = ["match_id", "championship_id", "location_id"]
    matches_dtf = pd.DataFrame(data=cursor.fetchall(),
                               columns=col_headers)

    matches_dtf = matches_dtf.drop(exclude_cols, axis=1)

    match_series = pd.DataFrame([match], columns=col_headers)
    match_series = match_series.drop(exclude_cols, axis=1)
    match_series[["home_score", "away_score"]] = match_series[["home_score", "away_score"]].fillna(np.nan)

    matches_dtf["match_win_type"] = matches_dtf["match_win_type"].str.strip()
    match_series["match_win_type"] = match_series["match_win_type"].str.strip()
    # check datatypes for each column
    matches_dtf = matches_dtf.astype(match_series.dtypes.to_dict())
    try:
        merged_dtfs = pd.merge(matches_dtf, match_series, how='inner')
        if merged_dtfs.empty:
            insert_sql = sql.SQL("INSERT INTO match ({}) VALUES ({})").format(
                sql.SQL(", ").join(map(sql.Identifier, match)),
                sql.SQL(", ").join(map(sql.Placeholder, match))
            )
            cursor.execute(insert_sql, match)
    except Exception as e:
        print(e)
    else:
        db_conn.commit()

    print("MATCH has been inserted!")
