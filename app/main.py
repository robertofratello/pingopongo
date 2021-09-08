# This is a sample Python script.

# Press Maiusc+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


from typing import Optional
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from elorepo import EloRepo
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

with open("../conf/origins.json", "r") as f:
    origins = json.load(f)
    print(origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],# origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Access-Control-Allow-Origin"]
)
VERSION = "1"
elo_repo = EloRepo()

@app.get("/api/health")
async def health():
    return f"pingopongo backend v{VERSION} is running"


@app.get("/api/v1/getelo/{name}/{db}")
async def ryead_item(name: str, db: Optional[str, None]):
    points, err = elo_repo.getone(name, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    print(points)
    return JSONResponse(points, 200)


@app.get("/api/v1/getelo/{db}")
async def get_rankings( db: Optional[str, None]):
    ranking, err = elo_repo.getall(db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(ranking, 200)


@app.post("/api/v1/match/{winner}/{loser}/{db}")
async def register_match(winner: str, loser: str, db: Optional[str, None]):
    err = elo_repo.register_match(winner, loser, db)
    return PlainTextResponse(err.text, err.code)


@app.get("/api/v1/games/{name}/{db}")
async def get_games(name: str, db: Optional[str, None]):
    games, err = elo_repo.get_games_for_player(name, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(games, 200)

@app.get("/api/v1/games/last/{n}/{db}")
async def get_last_n_games(n: int, db: Optional[str, None]):
    games, err = elo_repo.get_last_n_games(n, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(games, 200)

@app.post("/api/v1/undo/{db}")
async def undo( db: Optional[str, None]):
    err = elo_repo.undo(db)
    return PlainTextResponse(err.text, err.code)
