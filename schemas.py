from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlayerCreate(BaseModel):
    username: str
    discord_id: str | None = None


class ProfileUpdate(BaseModel):
    rank: str
    region: str


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game: str
    rank: str
    region: str


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    discord_id: str | None
    profiles: list[ProfileOut] = []


class ProfileSearchResult(BaseModel):
    player_id: int
    username: str
    discord_id: str | None
    game: str
    rank: str
    region: str

class SessionCreate(BaseModel):
    game: str
    # Only these two values are accepted, so a typo like "Win" is a 422 instead of a silent loss.
    result: Literal["win", "loss"]
    kills: int = Field(default=0, ge=0)
    deaths: int = Field(default=0, ge=0)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game: str
    result: str
    kills: int
    deaths: int
    played_at: datetime
    player_id: int

class PlayerStats(BaseModel):
    total_games: int
    wins: int
    losses: int
    win_rate: float
    total_kills: int
    total_deaths: int
    kd_ratio: float

class LeaderboardEntry(BaseModel):
    player_id: int
    username: str
    total_games: int
    wins: int
    win_rate: float