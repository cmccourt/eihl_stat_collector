import traceback

import psycopg2
from psycopg2 import sql, extras, pool

from settings.settings import postgres_db_config


# TODO use builder pattern to include OR statements
def generate_and_where_clause(params):
    return sql.SQL(" AND ").join(sql.Composed([sql.Composed([sql.Identifier(k),
                                                             sql.SQL("="), sql.Placeholder(k)]) for k, v in
                                               params.items()]))


class PostgresDBPool:
    db_conn_pool = pool.ThreadedConnectionPool(1, 20, user=postgres_db_config.un,
                                               password=postgres_db_config.pw,
                                               host=postgres_db_config.hostname,
                                               port="5432",
                                               database=postgres_db_config.db)

    def __init__(self):
        print("Create Postgres DB object")

    def __del__(self):
        self.release_pool()

    def release_pool(self):
        if self.db_conn_pool is not None:
            self.db_conn_pool.closeall()
        print("Postgres DB Pool is closed")


class EIHLPostgresHandler:
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
        "+/-": "+/-",
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
        "SVS%": "save_percentage"
    }

    def __init__(self, db_conn=None, db_cur=None):
        if not db_conn:
            db_conn = PostgresDBPool.db_conn_pool.getconn()
        self.db_conn = db_conn
        try:
            if not db_cur:
                db_cur = db_conn.cursor(cursor_factory=extras.DictCursor)
            self.db_cur = db_cur
        except psycopg2.Error:
            print("ERROR creating DB Cursor!")

    def shut_down(self):
        if self.db_conn:
            print("Put connection back into queue")
            self.db_conn.close()
            # PostgresDBPool.db_conn_pool.putconn(self.db_conn)
        if self.db_cur:
            self.db_cur.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shut_down()

    def __del__(self):
        self.shut_down()

    def as_string(self, _sql):
        if self.db_conn:
            text_string = _sql.as_string(self.db_conn)
            return text_string

    def print_sql_query(self, query, params):
        if self.db_conn:
            print(self.db_conn.mogrify(query, params))
        else:
            print("ERROR unable to print SQL! No DB connection available!\n")

    def fetch_all_data(self, query, params=None):
        try:
            self.db_cur.execute(query, params)
            result = self.db_cur.fetchall()
            return result
        except Exception:
            traceback.print_exc()

    def execute_query(self, query, params=None):
        try:
            self.db_cur.execute(query, params)
        except Exception:
            self.db_conn.rollback()
            traceback.print_exc()
        else:
            self.db_conn.commit()

    def insert_data(self, table: str, new_values: dict):
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, new_values)),
            sql.SQL(", ").join(map(sql.Placeholder, new_values))
        )
        try:
            # print(db_cur.mogrify(query, player_match_stats))
            self.execute_query(query, new_values)
            # db_cur.execute(query, player_match_stats)
        except TypeError:
            traceback.print_exc()

    def update_data(self, table: str, update_values: dict, where_clause: sql.SQL = None):
        if where_clause is None:
            where_clause = generate_and_where_clause(update_values)
        elif isinstance(where_clause, sql.Composable):
            where_clause = sql.SQL(self.as_string(where_clause))

        update_cols = sql.SQL(", ").join(sql.Composed(
            [sql.Composed([sql.Identifier(k),
                           sql.SQL("="),
                           sql.Placeholder(k)]) for k, v in update_values.items()]))
        try:
            # TODO Potential SQL injection
            query = sql.SQL("UPDATE {} SET {} WHERE {}").format(table, update_cols, where_clause)
            print(f"Updating existing stats data for Values: {update_values}")
            # print(db_cur.mogrify(query, player_match_stats))
            self.execute_query(query, update_values)
            # db_cur.execute(query, player_match_stats)
        except TypeError:
            traceback.print_exc()

    def check_for_dups(self, params: dict = None, query=None, table: str = None, where_clause: str = None) -> bool:
        records = []
        if where_clause is None:
            where_clause = generate_and_where_clause(params)
        if query is not None:
            records = self.fetch_all_data(query)
        else:
            dup_match_sql = sql.SQL("SELECT * FROM {} WHERE {}".format(
                sql.Identifier(table),
                self.as_string(where_clause)
            ))
            records = self.fetch_all_data(dup_match_sql, params)
        return True if len(records) > 0 else False
