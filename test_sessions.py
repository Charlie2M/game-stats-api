from conftest import as_player, create_player


def log_session(client, player, game="Valorant", result="win", kills=0, deaths=0):
    response = client.post(
        f"/players/{player['id']}/sessions",
        json={"game": game, "result": result, "kills": kills, "deaths": deaths},
        headers=as_player(player),
    )
    assert response.status_code == 200
    return response.json()


def test_log_session(client):
    player = create_player(client, "charlie", discord_id="123")
    session = log_session(client, player, kills=12, deaths=4)
    assert session["player_id"] == player["id"]
    assert session["result"] == "win"
    assert session["kills"] == 12


def test_log_session_for_missing_player(client):
    response = client.post(
        "/players/42/sessions", json={"game": "Valorant", "result": "win"}, headers={"X-Discord-User-Id": "123"}
    )
    assert response.status_code == 404


def test_session_result_must_be_win_or_loss(client):
    player = create_player(client, "charlie", discord_id="123")
    response = client.post(
        f"/players/{player['id']}/sessions", json={"game": "Valorant", "result": "Win"}, headers=as_player(player)
    )
    assert response.status_code == 422


def test_kills_and_deaths_cannot_be_negative(client):
    player = create_player(client, "charlie", discord_id="123")
    url = f"/players/{player['id']}/sessions"
    headers = as_player(player)
    assert client.post(url, json={"game": "Valorant", "result": "win", "kills": -1}, headers=headers).status_code == 422
    assert client.post(url, json={"game": "Valorant", "result": "win", "deaths": -1}, headers=headers).status_code == 422


def test_list_sessions(client):
    player = create_player(client, "charlie", discord_id="123")
    log_session(client, player, game="Valorant")
    log_session(client, player, game="League of Legends", result="loss")

    sessions = client.get(f"/players/{player['id']}/sessions").json()
    assert [s["game"] for s in sessions] == ["Valorant", "League of Legends"]


def test_update_session(client):
    player = create_player(client, "charlie", discord_id="123")
    session = log_session(client, player)
    url = f"/players/{player['id']}/sessions/{session['id']}"

    response = client.put(
        url, json={"game": "Valorant", "result": "loss", "kills": 3, "deaths": 9}, headers=as_player(player)
    )
    assert response.status_code == 200
    assert response.json()["result"] == "loss"
    assert response.json()["deaths"] == 9


def test_session_belongs_to_its_player(client):
    alice = create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    session = log_session(client, alice)

    # Bob's URL cannot reach Alice's session, even when Bob is the one asking.
    url = f"/players/{bob['id']}/sessions/{session['id']}"
    assert client.put(url, json={"game": "Valorant", "result": "loss"}, headers=as_player(bob)).status_code == 404
    assert client.delete(url, headers=as_player(bob)).status_code == 404


def test_delete_session(client):
    player = create_player(client, "charlie", discord_id="123")
    session = log_session(client, player)

    url = f"/players/{player['id']}/sessions/{session['id']}"
    assert client.delete(url, headers=as_player(player)).status_code == 204
    assert client.get(f"/players/{player['id']}/sessions").json() == []


def test_stats(client):
    player = create_player(client, "charlie", discord_id="123")
    log_session(client, player, result="win", kills=10, deaths=2)
    log_session(client, player, result="win", kills=5, deaths=3)
    log_session(client, player, result="loss", kills=0, deaths=5)

    assert client.get(f"/players/{player['id']}/stats").json() == {
        "total_games": 3,
        "wins": 2,
        "losses": 1,
        "win_rate": 66.7,
        "total_kills": 15,
        "total_deaths": 10,
        "kd_ratio": 1.5,
    }


def test_stats_with_no_sessions(client):
    player = create_player(client, "charlie", discord_id="123")
    stats = client.get(f"/players/{player['id']}/stats").json()
    assert stats["total_games"] == 0
    assert stats["wins"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["kd_ratio"] == 0.0


def test_stats_for_missing_player(client):
    assert client.get("/players/42/stats").status_code == 404


def test_leaderboard_sorts_by_wins_and_filters_by_game(client):
    alice = create_player(client, "alice", discord_id="1")
    bob = create_player(client, "bob", discord_id="2")
    log_session(client, alice, result="win")
    log_session(client, bob, result="win")
    log_session(client, bob, result="win")
    log_session(client, alice, game="League of Legends", result="win")
    log_session(client, alice, game="League of Legends", result="win")

    overall = client.get("/leaderboard").json()
    assert [entry["username"] for entry in overall] == ["alice", "bob"]
    assert overall[0]["wins"] == 3

    valorant = client.get("/leaderboard", params={"game": "Valorant"}).json()
    assert [entry["username"] for entry in valorant] == ["bob", "alice"]


def test_leaderboard_pagination(client):
    # Everyone has one win, so the order falls back to player id.
    for name in ["alice", "bob", "cara"]:
        player = create_player(client, name, discord_id=name)
        log_session(client, player)

    first_page = client.get("/leaderboard", params={"limit": 2}).json()
    second_page = client.get("/leaderboard", params={"limit": 2, "offset": 2}).json()
    assert [entry["username"] for entry in first_page] == ["alice", "bob"]
    assert [entry["username"] for entry in second_page] == ["cara"]

    assert client.get("/leaderboard", params={"limit": 0}).status_code == 422
