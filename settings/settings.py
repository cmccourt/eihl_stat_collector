postgres_db_config = {
    "un": "eihlstats",
    "pw": "20?6Lo5weLL",
    "db": "eihlstats",
    "hostname": "localhost",
    "port": "5432"}

mysql_prd_db_config = {
    "user": "root",
    "password": "6Lo5weLL",
    "database": "eihlstats",
    "host": "localhost",
    "port": "3306"}

mysql_dev_db_config = {
    "user": "root",
    "password": "6Lo5weLL",
    "database": "eihlstats_dev",
    "host": "localhost",
    "port": "3306"}

# eihl_base_url = "https://www.eliteleague.co.uk/"
# eihl_team_url = f"{eihl_base_url}team/"
# eihl_schedule_url = f"{eihl_base_url}schedule/"
# eihl_match_url = f"{eihl_base_url}game/"

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

eihl_teams = [
    "Belfast Giants",
    "Sheffield Steelers",
    "Cardiff Devils",
    "Coventry Blaze",
    "Dundee Stars",
    "Glasgow Clan",
    "Manchester Storm",
    "Fife Flyers",
    "Guildford Flames",
    "Nottingham Panthers"
]
