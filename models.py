from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    # Stored as a string because Discord IDs are 64-bit and JSON clients like JavaScript lose precision on them.
    discord_id = Column(String, unique=True, index=True, nullable=True)

    sessions = relationship("GameSession", back_populates="player")
    profiles = relationship("GameProfile", back_populates="player")


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


class GameProfile(Base):
    __tablename__ = "game_profiles"
    # One profile per player per game, so rank and region can differ between games.
    __table_args__ = (UniqueConstraint("player_id", "game"),)

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game = Column(String, nullable=False)
    rank = Column(String, nullable=False)
    region = Column(String, nullable=False)

    player = relationship("Player", back_populates="profiles")
