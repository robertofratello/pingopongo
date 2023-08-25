from typing import Optional
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from elorepo import EloRepo
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

with open("../conf/origins.json", "r") as f:
    origins = json.load(f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # origins,
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


@app.get("/api/v1/getelo/{name}")
async def read_item(name: str, db: str = ""):
    points, err = elo_repo.getone(name, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    print(points)
    return JSONResponse(points, 200)


@app.get("/api/v1/getelo")
async def get_rankings(db: str = ""):
    ranking, err = elo_repo.getall(db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(ranking, 200)


@app.get("/api/v1/preview/{winner}/{loser}")
async def preview_match(winner: str, loser: str, db: str = ""):
    winner_change, loser_change, err = elo_repo.compute_elo_change(
        winner, loser, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse((winner_change, loser_change))


@app.post("/api/v1/match/{winner}/{loser}")
async def register_match(winner: str, loser: str, db: str = ""):
    err = elo_repo.register_match(winner, loser, db)
    return PlainTextResponse(err.text, err.code)


@app.get("/api/v1/games/{name}")
async def get_games(name: str, db: str = ""):
    games, err = elo_repo.get_games_for_player(name, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(games, 200)


@app.get("/api/v1/games/last/{n}")
async def get_last_n_games(n: int, db: str = ""):
    games, err = elo_repo.get_last_n_games(n, db)
    if err:
        return PlainTextResponse(err.text, err.code)
    return JSONResponse(games, 200)


@app.post("/api/v1/undo")
async def undo(db: str = ""):
    err = elo_repo.undo(db)
    return PlainTextResponse(err.text, err.code)


@app.post("/api/v1/redo")
async def redo(db: str = ""):
    err = elo_repo.redo(db)
    return PlainTextResponse(err.text, err.code)
