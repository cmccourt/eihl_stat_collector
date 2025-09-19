from datetime import datetime

from fastapi import APIRouter
from pypika import MySQLQuery, Field

from backend.src.data_handlers.eihl_mysql import fetch_all_db_data

router = APIRouter()


@router.get("/match/{match_id}")
def match(match_id: int):
    match_query = MySQLQuery.from_("match").select("*").where(Field("match_id") == match_id)

    try:
        matches = fetch_all_db_data(match_query)
        if len(matches) == 0:
            print("There are no matches to update!")
    except Exception:
        matches = []
    return matches


@router.get("/matches/")
def matches(start_date: datetime = None, end_date: datetime = None, teams: list[str] = None,
            championships: list[str | int] = None):
    match_query = MySQLQuery.from_("match").select("*")

    if start_date is None:
        start_date = datetime.min
    if end_date is None:
        end_date = datetime.max
    match_query = match_query.where(Field("match_date")[start_date:end_date])

    if teams is not None:
        match_query = match_query.where(Field("home_team").isin(teams) | Field("away_team").isin(teams))

    if championships is not None:
        match_query = match_query.where(Field("home_team").isin(teams))

    matches = fetch_all_db_data(match_query)
    if len(matches) == 0:
        print("There are no matches to update!")
    return matches
