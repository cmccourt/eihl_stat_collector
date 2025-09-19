from fastapi import APIRouter
from pypika import MySQLQuery, Field, Table

from backend.src.data_handlers.eihl_mysql import fetch_all_db_data

router = APIRouter()


@router.get("/player_stats/{player_stats_id}")
def player_stats(player_stats_id: int, num_matches=5):
    stats_query = (MySQLQuery.from_("match_player_stats").select("*")
                   .where(Field("player_stat_id") == player_stats_id).limit(num_matches))
    try:
        stats = fetch_all_db_data(stats_query)
        if len(stats) == 0:
            print(f"There are no stats for match_id {player_stats_id}!")
    except Exception:
        stats = []
    return stats


@router.get("/player_match_stats/{match_id}")
def player_match_stats(match_id: int, player_name: str = None):
    # match_table = Table("match")
    player_stats_table = Table("match_player_stats")
    match_query = MySQLQuery.from_(player_stats_table).select("*")
    # .join(match_table).on(match_table.match_id == player_stats_table.match_id)

    if player_name is not None:
        match_query = match_query.where(
            (player_stats_table.match_id == match_id) & (Field("player_name") == player_name))
    else:
        match_query = match_query.where(player_stats_table.match_id == match_id)

    try:
        stats = fetch_all_db_data(match_query)
        if len(stats) == 0:
            print(f"The stats for match {match_id} does not exist!")
    except Exception:
        stats = []
    return stats
