from conftest import as_player, create_player


def test_create_player_rejects_taken_username(client):
    create_player(client, "charlie")
    response = client.post("/players", json={"username": "charlie"})
    assert response.status_code == 400


def test_get_player(client):
    player = create_player(client, "charlie")
    response = client.get(f"/players/{player['id']}")
    assert response.status_code == 200
    assert response.json()["username"] == "charlie"

    assert client.get("/players/42").status_code == 404


def test_update_player(client):
    player = create_player(client, "charlie", discord_id="123")
    response = client.put(
        f"/players/{player['id']}", json={"username": "charlie_2m", "discord_id": "123"}, headers=as_player(player)
    )
    assert response.status_code == 200
    assert response.json()["username"] == "charlie_2m"


def test_update_player_can_keep_own_username(client):
    player = create_player(client, "charlie", discord_id="123")
    response = client.put(
        f"/players/{player['id']}", json={"username": "charlie", "discord_id": "123"}, headers=as_player(player)
    )
    assert response.status_code == 200


def test_update_player_rejects_taken_username_and_discord_id(client):
    create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    url = f"/players/{bob['id']}"

    assert client.put(url, json={"username": "alice", "discord_id": "2"}, headers=as_player(bob)).status_code == 400
    assert client.put(url, json={"username": "bob", "discord_id": "1"}, headers=as_player(bob)).status_code == 400


def test_update_missing_player(client):
    response = client.put("/players/42", json={"username": "charlie"}, headers={"X-Discord-User-Id": "123"})
    assert response.status_code == 404


def test_delete_player_also_deletes_sessions_and_profiles(client):
    player = create_player(client, "charlie", discord_id="123")
    url = f"/players/{player['id']}"
    client.post(f"{url}/sessions", json={"game": "Valorant", "result": "win"}, headers=as_player(player))
    client.put(f"{url}/profiles/Valorant", json={"rank": "Gold", "region": "EU"}, headers=as_player(player))

    assert client.delete(url, headers=as_player(player)).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get("/leaderboard").json() == []
    assert client.get("/profiles", params={"game": "Valorant"}).json() == []


def test_delete_missing_player(client):
    assert client.delete("/players/42", headers={"X-Discord-User-Id": "123"}).status_code == 404
