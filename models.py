from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)

    sessions = relationship("GameSession", back_populates="player")


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game = Column(String, nullable=False)
    result = Column(String, nullable=False)
    kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    played_at = Column(DateTime(timezone=True), server_default=func.now())

    player = relationship("Player", back_populates="sessions")