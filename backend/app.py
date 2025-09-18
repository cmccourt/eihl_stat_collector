import uvicorn
from fastapi import FastAPI

from routers import matches

app = FastAPI(title="Elite League Stats API")

app.include_router(matches.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Hello World"}


if __name__ == '__main__':
    uvicorn.run("app:app")
