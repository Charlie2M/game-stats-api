import main
from conftest import as_player, create_player

SESSION = {"game": "Valorant", "result": "win"}


def test_create_player_needs_bot_key(client):
    del client.headers["X-API-Key"]
    assert client.post("/players", json={"username": "charlie"}).status_code == 401


def test_wrong_bot_key_is_rejected(client):
    response = client.post("/players", json={"username": "charlie"}, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_writes_are_refused_when_server_has_no_key(client, monkeypatch):
    # A server started without BOT_API_KEY must not accept writes from anyone.
    monkeypatch.setattr(main, "BOT_API_KEY", None)
    assert client.post("/players", json={"username": "charlie"}).status_code == 401


def test_player_cannot_log_session_for_someone_else(client):
    alice = create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    response = client.post(f"/players/{alice['id']}/sessions", json=SESSION, headers=as_player(bob))
    assert response.status_code == 403


def test_player_cannot_edit_or_delete_someone_else(client):
    alice = create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    url = f"/players/{alice['id']}"

    assert client.put(url, json={"username": "hacked"}, headers=as_player(bob)).status_code == 403
    assert client.delete(url, headers=as_player(bob)).status_code == 403
    profile = {"rank": "Iron", "region": "EU"}
    assert client.put(f"{url}/profiles/Valorant", json=profile, headers=as_player(bob)).status_code == 403


def test_writes_to_a_player_need_discord_id_header(client):
    player = create_player(client, "charlie", discord_id="123")
    assert client.post(f"/players/{player['id']}/sessions", json=SESSION).status_code == 422


def test_writes_to_a_player_need_bot_key(client):
    player = create_player(client, "charlie", discord_id="123")
    del client.headers["X-API-Key"]
    response = client.post(f"/players/{player['id']}/sessions", json=SESSION, headers=as_player(player))
    assert response.status_code == 401


def test_player_without_discord_account_cannot_be_changed(client):
    player = create_player(client, "charlie")
    response = client.post(f"/players/{player['id']}/sessions", json=SESSION, headers={"X-Discord-User-Id": "123"})
    assert response.status_code == 403


def test_reads_do_not_need_auth(client):
    player = create_player(client, "charlie")
    del client.headers["X-API-Key"]
    assert client.get(f"/players/{player['id']}").status_code == 200
    assert client.get(f"/players/{player['id']}/stats").status_code == 200
    assert client.get("/leaderboard").status_code == 200
