import uvicorn
from fastapi import FastAPI

from routers import team_match_stats, matches, player_match_stats

app = FastAPI(title="Elite League Stats API")

app.include_router(matches.router, prefix="/api")
app.include_router(team_match_stats.router, prefix="/api")
app.include_router(player_match_stats.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Hello World"}


if __name__ == '__main__':
    uvicorn.run("app:app")
