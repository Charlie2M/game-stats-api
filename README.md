# Game Stats API

A REST API for tracking players and game sessions for a small gaming community, built with FastAPI and SQLAlchemy. Not tied to a single game, `game` is just a field on each session, so it works for any title a group plays.

## Features

- Register players and look them up
- Log game sessions (game, result, kills, deaths) tied to a player
- Pull a player's aggregate stats: total games, wins, losses, win rate, K/D ratio
- Leaderboard endpoint, optionally filtered by game

## Tech stack

- Python 3
- [FastAPI](https://fastapi.tiangolo.com/) for the API layer, with auto-generated interactive docs at `/docs`
- [SQLAlchemy](https://www.sqlalchemy.org/) as the ORM
- SQLite for storage

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/players` | Register a new player |
| GET | `/players/{player_id}` | Get a player by id |
| POST | `/players/{player_id}/sessions` | Log a game session for a player |
| GET | `/players/{player_id}/stats` | Get a player's aggregate stats (win rate, K/D) |
| GET | `/leaderboard` | Leaderboard sorted by wins, optionally filtered with `?game=` |

## Setup

```bash
git clone https://github.com/Charlie2M/game-stats-api.git
cd game-stats-api
python -m venv venv
venv\Scripts\activate  # source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` to explore and test the API interactively. The SQLite database file (`game_stats.db`) is created automatically on first run and is not tracked in git.

## Example

```bash
# Register a player
POST /players
{"username": "charlie_2m"}

# Log a session
POST /players/1/sessions
{"game": "Valorant", "result": "win", "kills": 12, "deaths": 4}

# Get stats
GET /players/1/stats

# Leaderboard for a specific game
GET /leaderboard?game=Valorant
```

## Roadmap

- Delete/update endpoints for players and sessions
- Basic auth so only a player (or a linked Discord account) can log their own sessions
- Could serve as the backend for [LFGBot](https://github.com/Charlie2M/lfgbot)'s planned rank/server filtering feature

## Status

Early-stage personal project, actively developed.
