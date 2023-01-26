import traceback

from mysql.connector import connect, connection

from settings.settings import MySQLDBConfig


def generate_and_where_clause(params):
    return " AND ".join([f"{k}=%({k})s" for k, v in params.items()])


class EIHLMysqlHandler:
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
        "SVS%": "save_percentage"
    }

    def __init__(self, db_conn: connection = None):
        self.db_conn: connection = db_conn
        if not self.db_conn:
            self.db_conn = connect(pool_size=1,
                                   user=MySQLDBConfig.un,
                                   password=MySQLDBConfig.pw,
                                   host=MySQLDBConfig.hostname,
                                   port=MySQLDBConfig.port,
                                   database=MySQLDBConfig.db)

    def shut_down(self):
        if self.db_conn:
            self.db_conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shut_down()

    def __del__(self):
        self.shut_down()

    def print_sql_query(self, query, params):
        if self.db_conn:
            print(self.db_conn.mogrify(query, params))
        else:
            print("ERROR unable to print SQL! No DB connection available!\n")

    def fetch_all_data(self, query, params=None):
        try:
            with self.db_conn.cursor(dictionary=True) as db_cur:
                db_cur.execute(query, params)
                result = db_cur.fetchall()
                return result
        except Exception:
            traceback.print_exc()

    def execute_query(self, query, params=None):
        with self.db_conn.cursor(dictionary=True) as db_cur:
            try:
                db_cur.execute(query, params)
            except Exception:
                self.db_conn.rollback()
                traceback.print_exc()
                self.print_sql_query(query, params)
            else:
                self.db_conn.commit()

    def insert_data(self, table: str, new_val_dict: dict):

        query = "INSERT INTO {} ({}) VALUES ({})".format(
            f"`{table}`" if table[0] != "`" and table[len(table) - 1] != "`" else table,
            ", ".join(new_val_dict),
            ", ".join([f"%({x})s" for x in new_val_dict])
        )
        try:
            # print(db_cur.mogrify(query, player_match_stats))
            self.execute_query(query, new_val_dict)
            # db_cur.execute(query, player_match_stats)
        except TypeError:
            traceback.print_exc()

    def update_data(self, table: str, update_values: dict, where_clause: str = None):
        if where_clause is None:
            where_clause = generate_and_where_clause(update_values)

        update_cond = ", ".join([f"{k}=%({k})s" for k, v in update_values.items()])
        try:
            query = "UPDATE {} SET {} WHERE {}".format(
                f"`{table}`" if table[0] != "`" and table[len(table) - 1] != "`" else table,
                update_cond, where_clause)
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
            # test = self.as_string(where_clause)
            dup_match_sql = "SELECT * FROM {} WHERE {}".format(
                f"`{table}`" if table[0] != "`" and table[len(table) - 1] != "`" else table,
                where_clause
            )
            records = self.fetch_all_data(dup_match_sql, params)
        return True if len(records) > 0 else False