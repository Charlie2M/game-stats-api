# Game Stats API

A REST API for tracking players and game sessions for a small gaming community, built with FastAPI and SQLAlchemy. Not tied to a single game, `game` is just a field on each session, so it works for any title a group plays.

## Features

- Register players (optionally linked to a Discord account) and look them up
- Store a rank and region per player per game, and search profiles by game and region
- Log, list, edit, and delete game sessions (game, win or loss, kills, deaths) tied to a player
- Edit and delete players (deleting a player also deletes their sessions and profiles)
- Writes are limited to [LFGBot](https://github.com/Charlie2M/lfgbot), and a player can only change their own data
- Pull a player's aggregate stats: total games, wins, losses, win rate, K/D ratio
- Leaderboard endpoint, optionally filtered by game, with `limit`/`offset` pagination

## Tech stack

- Python 3
- [FastAPI](https://fastapi.tiangolo.com/) for the API layer, with auto-generated interactive docs at `/docs`
- [SQLAlchemy](https://www.sqlalchemy.org/) as the ORM
- SQLite for storage
- pytest and FastAPI's `TestClient` for tests

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/players` | Register a new player |
| GET | `/players/{player_id}` | Get a player by id |
| PUT | `/players/{player_id}` | Replace a player's username and Discord ID |
| DELETE | `/players/{player_id}` | Delete a player with their sessions and profiles |
| POST | `/players/{player_id}/sessions` | Log a game session for a player (`result` is `"win"` or `"loss"`) |
| GET | `/players/{player_id}/sessions` | List a player's sessions |
| PUT | `/players/{player_id}/sessions/{session_id}` | Replace a session |
| DELETE | `/players/{player_id}/sessions/{session_id}` | Delete a session |
| GET | `/players/by-discord/{discord_id}` | Get a player by linked Discord account (404 if none) |
| PUT | `/players/{player_id}/profiles/{game}` | Create or replace a player's rank and region for one game |
| GET | `/profiles?game=&region=` | Find profiles for a game, optionally in one region |
| GET | `/players/{player_id}/stats` | Get a player's aggregate stats (win rate, K/D) |
| GET | `/leaderboard?game=&limit=&offset=` | Leaderboard sorted by wins, optionally filtered by game (10 per page by default, max 100) |

GET endpoints are public. Every POST, PUT, and DELETE needs auth (see below).

## Auth

The API is written for one trusted client, LFGBot, which shares a secret key with the server.

- Every write sends the key in an `X-API-Key` header. A missing or wrong key gets a 401.
- Writes to an existing player (anything under `/players/{player_id}`) also send `X-Discord-User-Id`, the Discord ID of whoever ran the bot command. If it doesn't match that player's linked Discord account, the request gets a 403. So a player can only log, edit, or delete their own sessions, profiles, and player.
- Registering (`POST /players`) only needs the key.

The API trusts the bot to send the right Discord ID, which is why the key must stay secret. A player with no linked Discord account can't be changed after registering.

## Setup

```bash
git clone https://github.com/Charlie2M/game-stats-api.git
cd game-stats-api
python -m venv venv
venv\Scripts\activate  # source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Set the bot key (any long random string; LFGBot needs the same value), then start the server:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"   # generates a key
$env:BOT_API_KEY = "paste-the-key-here"   # PowerShell; use export BOT_API_KEY=... on macOS/Linux
uvicorn main:app --reload
```

If `BOT_API_KEY` isn't set, the server still starts but refuses every write. Then open `http://127.0.0.1:8000/docs` to explore and test the API interactively (the auth headers appear as fields on each write endpoint). The SQLite database file (`game_stats.db`) is created automatically on first run and is not tracked in git. There are no migrations, so after pulling a change to the models, delete `game_stats.db` to recreate it (this deletes your local data).

Run the tests with:

```bash
pytest
```

## Example

```bash
# Register a player linked to a Discord account
POST /players
X-API-Key: <bot key>
{"username": "charlie_2m", "discord_id": "123456789012345678"}

# Log a session (as that player)
POST /players/1/sessions
X-API-Key: <bot key>
X-Discord-User-Id: 123456789012345678
{"game": "Valorant", "result": "win", "kills": 12, "deaths": 4}

# Get stats
GET /players/1/stats

# Fix a typo in that session (PUT replaces the whole session, same headers as above)
PUT /players/1/sessions/1
{"game": "Valorant", "result": "win", "kills": 14, "deaths": 4}

# Leaderboard for a specific game, second page of 10
GET /leaderboard?game=Valorant&offset=10

# Set a Valorant profile (same headers as above)
PUT /players/1/profiles/Valorant
{"rank": "Gold", "region": "EU"}

# Find Valorant players in Europe
GET /profiles?game=Valorant&region=EU
```

## Roadmap

- Backend for [LFGBot](https://github.com/Charlie2M/lfgbot)'s rank/server filtering (done for Valorant via the profile endpoints)

## Status

Early-stage personal project, actively developed.
