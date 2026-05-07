from io import BytesIO


def test_auth_me_and_default_playlist(client):
    login = client.get("/v1/auth/oauth/github/callback?code=auth-smoke")
    assert login.status_code == 200
    token = login.json()["data"]["token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    me_payload = me.json()["data"]
    assert me_payload["username"].startswith("github_user_")
    assert len(me_payload["oauths"]) == 1

    playlists = client.get("/v1/playlists", headers={"Authorization": f"Bearer {token}"})
    assert playlists.status_code == 200
    items = playlists.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["is_default"] is True
    assert items[0]["title"] == "我的收藏"


def test_upload_and_asr_flow(client, auth_headers):
    image_upload = client.post(
        "/v1/upload/image",
        headers=auth_headers,
        files={"file": ("cover.png", b"fake-png-data", "image/png")},
    )
    assert image_upload.status_code == 200
    image_url = image_upload.json()["data"]["url"]
    assert image_url.startswith("/static/uploads/images/")

    audio_upload = client.post(
        "/v1/upload/audio",
        headers=auth_headers,
        files={"file": ("voice.wav", b"RIFFfakewave", "audio/wav")},
    )
    assert audio_upload.status_code == 200
    audio_url = audio_upload.json()["data"]["url"]
    assert audio_url.startswith("/static/uploads/audio/")

    asr = client.post(
        "/v1/asr/transcribe",
        headers=auth_headers,
        files={"file": ("voice.wav", b"RIFFfakewave", "audio/wav")},
        data={"language": "zh"},
    )
    assert asr.status_code == 200
    payload = asr.json()["data"]
    assert payload["language"] == "zh"
    assert "voice.wav" in payload["text"]


def test_song_playlist_plaza_and_favorites_flow(client):
    owner_login = client.get("/v1/auth/oauth/github/callback?code=owner001")
    owner_token = owner_login.json()["data"]["token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "Accept": "text/event-stream"}

    prompt_response = client.post(
        "/v1/songs/generate/prompt",
        headers=owner_headers,
        json={"prompt": "warm synth pop", "lyrics": "hello world", "is_instrumental": False},
    )
    assert prompt_response.status_code == 200
    from app.tests.conftest import parse_sse_events

    events = parse_sse_events(prompt_response.text)
    assert len(events) >= 2
    assert events[-1]["data"]["status"] == 2
    song = events[-1]["data"]["song"]
    song_id = song["id"]

    songs = client.get("/v1/songs", headers={"Authorization": f"Bearer {owner_token}"})
    assert songs.status_code == 200
    assert songs.json()["data"]["total"] == 1

    publish = client.post(
        f"/v1/songs/{song_id}/publish",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"is_public": True},
    )
    assert publish.status_code == 200
    assert publish.json()["data"]["is_public"] is True

    create_playlist = client.post(
        "/v1/playlists",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Road Trip", "description": "mix", "is_public": False},
    )
    assert create_playlist.status_code == 200
    playlist_id = create_playlist.json()["data"]["id"]

    add_song = client.post(
        f"/v1/playlists/{playlist_id}/songs",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"song_id": song_id},
    )
    assert add_song.status_code == 200
    assert add_song.json()["data"]["songs_count"] == 1

    plaza = client.get("/v1/plaza")
    assert plaza.status_code == 200
    assert plaza.json()["data"]["total"] == 1

    liker_login = client.get("/v1/auth/oauth/github/callback?code=liker002")
    liker_token = liker_login.json()["data"]["token"]
    like = client.post(f"/v1/favorites/{song_id}", headers={"Authorization": f"Bearer {liker_token}"})
    assert like.status_code == 200

    plaza_detail = client.get(f"/v1/plaza/{song_id}")
    assert plaza_detail.status_code == 200
    assert plaza_detail.json()["data"]["likes_count"] == 1

    unlike = client.delete(f"/v1/favorites/{song_id}", headers={"Authorization": f"Bearer {liker_token}"})
    assert unlike.status_code == 200
