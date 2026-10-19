import os
import secrets

from fastapi import FastAPI, Depends, Header, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI()

# LFGBot's shared secret. It comes from the environment so it never ends up in git.
BOT_API_KEY = os.environ.get("BOT_API_KEY")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_player_or_404(db: Session, player_id: int) -> models.Player:
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def get_session_or_404(db: Session, player_id: int, session_id: int) -> models.GameSession:
    # Filtering on player_id too means a session can only be reached through the player who owns it.
    session = db.query(models.GameSession).filter(
        models.GameSession.id == session_id,
        models.GameSession.player_id == player_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def check_player_is_unique(db: Session, player: schemas.PlayerCreate, current_id: int | None = None):
    # current_id is the player being updated, so they don't clash with their own username.
    taken = db.query(models.Player).filter(models.Player.username == player.username).first()
    if taken and taken.id != current_id:
        raise HTTPException(status_code=400, detail="Username already registered")
    if player.discord_id:
        linked = db.query(models.Player).filter(models.Player.discord_id == player.discord_id).first()
        if linked and linked.id != current_id:
            raise HTTPException(status_code=400, detail="Discord account already linked to a player")


def require_bot_key(x_api_key: str | None = Header(default=None)):
    # If BOT_API_KEY is not set, every write is refused instead of being left open.
    # compare_digest takes the same time however many characters match, so the key can't be guessed one character at a time.
    if not BOT_API_KEY or x_api_key is None or not secrets.compare_digest(x_api_key, BOT_API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


def get_own_player(
    player_id: int,
    x_discord_user_id: str = Header(),
    db: Session = Depends(get_db),
    _: None = Depends(require_bot_key),
) -> models.Player:
    # The bot key proves the request came from LFGBot, and LFGBot sends the Discord ID of whoever ran the command.
    # So a player can only change their own data, and a player with no linked Discord account can't be changed at all.
    player = get_player_or_404(db, player_id)
    if player.discord_id != x_discord_user_id:
        raise HTTPException(status_code=403, detail="You can only change your own player")
    return player


@app.get("/")
def read_root():
    return {"status": "alive"}


# Registering only needs the bot key, since the new player has no data to protect yet.
@app.post("/players", response_model=schemas.PlayerOut, dependencies=[Depends(require_bot_key)])
def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    check_player_is_unique(db, player)

    new_player = models.Player(username=player.username, discord_id=player.discord_id)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@app.get("/players/{player_id}", response_model=schemas.PlayerOut)
def get_player(player_id: int, db: Session = Depends(get_db)):
    return get_player_or_404(db, player_id)


@app.put("/players/{player_id}", response_model=schemas.PlayerOut)
def update_player(
    player: schemas.PlayerCreate,
    existing: models.Player = Depends(get_own_player),
    db: Session = Depends(get_db),
):
    # FastAPI reuses one get_db result per request, so this db is the same session get_own_player loaded existing with.
    check_player_is_unique(db, player, current_id=existing.id)

    # PUT replaces the whole player, so leaving out discord_id unlinks the Discord account.
    existing.username = player.username
    existing.discord_id = player.discord_id
    db.commit()
    db.refresh(existing)
    return existing


@app.delete("/players/{player_id}", status_code=204)
def delete_player(player: models.Player = Depends(get_own_player), db: Session = Depends(get_db)):
    db.delete(player)
    db.commit()


@app.get("/players/by-discord/{discord_id}", response_model=schemas.PlayerOut)
def get_player_by_discord(discord_id: str, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.put("/players/{player_id}/profiles/{game}", response_model=schemas.ProfileOut)
def set_profile(
    game: str,
    profile: schemas.ProfileUpdate,
    player: models.Player = Depends(get_own_player),
    db: Session = Depends(get_db),
):
    # PUT creates the profile the first time and replaces it after that.
    existing = db.query(models.GameProfile).filter(
        models.GameProfile.player_id == player.id,
        models.GameProfile.game == game,
    ).first()
    if existing:
        existing.rank = profile.rank
        existing.region = profile.region
        saved = existing
    else:
        saved = models.GameProfile(player_id=player.id, game=game, **profile.model_dump())
        db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@app.get("/profiles", response_model=list[schemas.ProfileSearchResult])
def search_profiles(game: str, region: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.GameProfile, models.Player).join(
        models.Player, models.GameProfile.player_id == models.Player.id
    ).filter(models.GameProfile.game == game)

    if region:
        query = query.filter(models.GameProfile.region == region)

    return [
        schemas.ProfileSearchResult(
            player_id=player.id, username=player.username, discord_id=player.discord_id,
            game=profile.game, rank=profile.rank, region=profile.region,
        )
        for profile, player in query.all()
    ]


@app.post("/players/{player_id}/sessions", response_model=schemas.SessionOut)
def log_session(
    session: schemas.SessionCreate,
    player: models.Player = Depends(get_own_player),
    db: Session = Depends(get_db),
):
    new_session = models.GameSession(player_id=player.id, **session.model_dump())
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@app.get("/players/{player_id}/sessions", response_model=list[schemas.SessionOut])
def list_sessions(player_id: int, db: Session = Depends(get_db)):
    get_player_or_404(db, player_id)
    return db.query(models.GameSession).filter(
        models.GameSession.player_id == player_id
    ).order_by(models.GameSession.id).all()


@app.put("/players/{player_id}/sessions/{session_id}", response_model=schemas.SessionOut)
def update_session(
    session_id: int,
    session: schemas.SessionCreate,
    player: models.Player = Depends(get_own_player),
    db: Session = Depends(get_db),
):
    existing = get_session_or_404(db, player.id, session_id)
    for field, value in session.model_dump().items():
        setattr(existing, field, value)
    db.commit()
    db.refresh(existing)
    return existing


@app.delete("/players/{player_id}/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, player: models.Player = Depends(get_own_player), db: Session = Depends(get_db)):
    session = get_session_or_404(db, player.id, session_id)
    db.delete(session)
    db.commit()


@app.get("/players/{player_id}/stats", response_model=schemas.PlayerStats)
def get_player_stats(player_id: int, db: Session = Depends(get_db)):
    get_player_or_404(db, player_id)

    # One query computes all four numbers. SUM returns NULL when there are no rows, hence the "or 0".
    total_games, wins, total_kills, total_deaths = db.query(
        func.count(models.GameSession.id),
        func.sum(case((models.GameSession.result == "win", 1), else_=0)),
        func.sum(models.GameSession.kills),
        func.sum(models.GameSession.deaths),
    ).filter(models.GameSession.player_id == player_id).one()
    wins = wins or 0
    total_kills = total_kills or 0
    total_deaths = total_deaths or 0

    losses = total_games - wins
    win_rate = round(wins / total_games * 100, 1) if total_games else 0.0
    kd_ratio = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills)

    return schemas.PlayerStats(
        total_games=total_games,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        total_kills=total_kills,
        total_deaths=total_deaths,
        kd_ratio=kd_ratio,
    )


@app.get("/leaderboard", response_model=list[schemas.LeaderboardEntry])
def get_leaderboard(
    game: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    wins = func.sum(case((models.GameSession.result == "win", 1), else_=0)).label("wins")
    query = db.query(
        models.Player.id,
        models.Player.username,
        func.count(models.GameSession.id).label("total_games"),
        wins,
    ).join(models.GameSession, models.GameSession.player_id == models.Player.id)

    if game:
        query = query.filter(models.GameSession.game == game)

    # Player.id breaks ties, so players with equal wins keep the same order on every page.
    query = query.group_by(models.Player.id).order_by(wins.desc(), models.Player.id)
    query = query.offset(offset).limit(limit)

    leaderboard = []
    for player_id, username, total_games, player_wins in query.all():
        win_rate = round(player_wins / total_games * 100, 1) if total_games else 0.0
        leaderboard.append(schemas.LeaderboardEntry(
            player_id=player_id, username=username,
            total_games=total_games, wins=player_wins, win_rate=win_rate,
        ))
    return leaderboard
