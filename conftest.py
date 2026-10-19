# pytest loads this file automatically, so every test file can use the client fixture.
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database import Base
from main import app, get_db

BOT_KEY = "test-bot-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Each test gets its own empty SQLite file, so tests never touch game_stats.db or each other.
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Tests act as LFGBot, so every request sends the bot key unless a test overrides it.
    monkeypatch.setattr(main, "BOT_API_KEY", BOT_KEY)
    yield TestClient(app, headers={"X-API-Key": BOT_KEY})
    app.dependency_overrides.clear()
    engine.dispose()


def create_player(client, username, discord_id=None):
    response = client.post("/players", json={"username": username, "discord_id": discord_id})
    assert response.status_code == 200
    return response.json()


def as_player(player):
    # The header LFGBot sends with the Discord ID of whoever ran the command.
    return {"X-Discord-User-Id": player["discord_id"]}
