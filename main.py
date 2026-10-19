from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"status": "alive"}


@app.post("/players", response_model=schemas.PlayerOut)
def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Player).filter(models.Player.username == player.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    if player.discord_id:
        linked = db.query(models.Player).filter(models.Player.discord_id == player.discord_id).first()
        if linked:
            raise HTTPException(status_code=400, detail="Discord account already linked to a player")

    new_player = models.Player(username=player.username, discord_id=player.discord_id)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@app.get("/players/{player_id}", response_model=schemas.PlayerOut)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.get("/players/by-discord/{discord_id}", response_model=schemas.PlayerOut)
def get_player_by_discord(discord_id: str, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.put("/players/{player_id}/profiles/{game}", response_model=schemas.ProfileOut)
def set_profile(player_id: int, game: str, profile: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # PUT creates the profile the first time and replaces it after that.
    existing = db.query(models.GameProfile).filter(
        models.GameProfile.player_id == player_id,
        models.GameProfile.game == game,
    ).first()
    if existing:
        existing.rank = profile.rank
        existing.region = profile.region
        saved = existing
    else:
        saved = models.GameProfile(player_id=player_id, game=game, **profile.model_dump())
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
def log_session(player_id: int, session: schemas.SessionCreate, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    new_session = models.GameSession(player_id=player_id, **session.model_dump())
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.get("/players/{player_id}/stats", response_model=schemas.PlayerStats)
def get_player_stats(player_id: int, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    total_games = db.query(func.count(models.GameSession.id)).filter(
        models.GameSession.player_id == player_id
    ).scalar()

    wins = db.query(func.count(models.GameSession.id)).filter(
        models.GameSession.player_id == player_id,
        models.GameSession.result == "win"
    ).scalar()

    total_kills = db.query(func.sum(models.GameSession.kills)).filter(
        models.GameSession.player_id == player_id
    ).scalar() or 0

    total_deaths = db.query(func.sum(models.GameSession.deaths)).filter(
        models.GameSession.player_id == player_id
    ).scalar() or 0

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
def get_leaderboard(game: str | None = None, db: Session = Depends(get_db)):
    query = db.query(
        models.Player.id,
        models.Player.username,
        func.count(models.GameSession.id).label("total_games"),
        func.sum(case((models.GameSession.result == "win", 1), else_=0)).label("wins"),
    ).join(models.GameSession, models.GameSession.player_id == models.Player.id)

    if game:
        query = query.filter(models.GameSession.game == game)

    query = query.group_by(models.Player.id).order_by(
        func.sum(case((models.GameSession.result == "win", 1), else_=0)).desc()
    )

    leaderboard = []
    for player_id, username, total_games, wins in query.all():
        win_rate = round(wins / total_games * 100, 1) if total_games else 0.0
        leaderboard.append(schemas.LeaderboardEntry(
            player_id=player_id, username=username,
            total_games=total_games, wins=wins, win_rate=win_rate,
        ))
    return leaderboard