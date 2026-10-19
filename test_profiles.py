from conftest import as_player, create_player


def test_create_player_with_discord_id(client):
    player = create_player(client, "charlie", discord_id="123")
    assert player["discord_id"] == "123"
    assert player["profiles"] == []


def test_discord_id_must_be_unique(client):
    create_player(client, "charlie", discord_id="123")
    response = client.post("/players", json={"username": "someone_else", "discord_id": "123"})
    assert response.status_code == 400


def test_get_player_by_discord(client):
    create_player(client, "charlie", discord_id="123")
    response = client.get("/players/by-discord/123")
    assert response.status_code == 200
    assert response.json()["username"] == "charlie"

    assert client.get("/players/by-discord/999").status_code == 404


def test_set_profile_creates_then_updates(client):
    player = create_player(client, "charlie", discord_id="123")
    url = f"/players/{player['id']}/profiles/Valorant"

    response = client.put(url, json={"rank": "Gold", "region": "EU"}, headers=as_player(player))
    assert response.status_code == 200
    assert response.json() == {"game": "Valorant", "rank": "Gold", "region": "EU"}

    client.put(url, json={"rank": "Platinum", "region": "EU"}, headers=as_player(player))
    profiles = client.get("/players/by-discord/123").json()["profiles"]
    assert profiles == [{"game": "Valorant", "rank": "Platinum", "region": "EU"}]


def test_set_profile_for_missing_player(client):
    response = client.put(
        "/players/42/profiles/Valorant", json={"rank": "Gold", "region": "EU"}, headers={"X-Discord-User-Id": "123"}
    )
    assert response.status_code == 404


def test_search_profiles_filters_by_game_and_region(client):
    alice = create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    cara = create_player(client, "cara", discord_id="3")
    client.put(f"/players/{alice['id']}/profiles/Valorant", json={"rank": "Gold", "region": "EU"}, headers=as_player(alice))
    client.put(f"/players/{bob['id']}/profiles/Valorant", json={"rank": "Silver", "region": "NA"}, headers=as_player(bob))
    client.put(
        f"/players/{cara['id']}/profiles/League of Legends", json={"rank": "Gold", "region": "EU"}, headers=as_player(cara)
    )

    everyone = client.get("/profiles", params={"game": "Valorant"}).json()
    assert {p["username"] for p in everyone} == {"alice", "bob"}

    eu_only = client.get("/profiles", params={"game": "Valorant", "region": "EU"}).json()
    assert eu_only == [{
        "player_id": alice["id"], "username": "alice", "discord_id": "1",
        "game": "Valorant", "rank": "Gold", "region": "EU",
    }]
