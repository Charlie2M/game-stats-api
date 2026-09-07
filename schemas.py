from pydantic import BaseModel
from datetime import datetime


class PlayerCreate(BaseModel):
    username: str


class PlayerOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    game: str
    result: str
    kills: int = 0
    deaths: int = 0


class SessionOut(BaseModel):
    id: int
    game: str
    result: str
    kills: int
    deaths: int
    played_at: datetime
    player_id: int

class Config:
        from_attributes = True

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