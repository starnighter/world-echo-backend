from app.tests.conftest import parse_sse_events


def test_prompt_generation_sse(client, auth_headers):
    response = client.post(
        "/v1/songs/generate/prompt",
        headers={**auth_headers, "Accept": "text/event-stream"},
        json={"prompt": "dreamy lo-fi", "lyrics": "night sky"},
    )
    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events[0]["data"]["status"] == 1
    assert events[-1]["data"]["status"] == 2
    assert events[-1]["data"]["song"]["source_type"] == "prompt"
    assert events[-1]["data"]["song"]["cover_url"] in {str(i) for i in range(1, 9)}


def test_image_generation_sse(client, auth_headers):
    upload = client.post(
        "/v1/upload/image",
        headers=auth_headers,
        files={"file": ("photo.png", b"mock-image", "image/png")},
    )
    image_url = upload.json()["data"]["url"]
    response = client.post(
        "/v1/songs/generate/image",
        headers={**auth_headers, "Accept": "text/event-stream"},
        json={"source_url": image_url, "prompt": "gentle folk"},
    )
    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events[-1]["data"]["status"] == 2
    assert events[-1]["data"]["song"]["source_type"] == "image"
    assert events[-1]["data"]["song"]["music_url"].startswith("/static/generated/music/")
    assert events[-1]["data"]["song"]["cover_url"] in {str(i) for i in range(1, 9)}


def test_voice_generation_sse(client, auth_headers):
    upload = client.post(
        "/v1/upload/audio",
        headers=auth_headers,
        files={"file": ("voice.wav", b"RIFFvoice", "audio/wav")},
    )
    audio_url = upload.json()["data"]["url"]
    response = client.post(
        "/v1/songs/generate/voice",
        headers={**auth_headers, "Accept": "text/event-stream"},
        json={"source_url": audio_url, "prompt": "electro pop"},
    )
    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events[-1]["data"]["status"] == 2
    assert events[-1]["data"]["song"]["source_type"] == "voice"
    assert "asr_text" in events[-1]["data"]["song"]["extracted_data"]
    assert events[-1]["data"]["song"]["cover_url"] in {str(i) for i in range(1, 9)}
