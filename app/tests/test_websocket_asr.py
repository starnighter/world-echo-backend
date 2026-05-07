def test_realtime_asr_websocket(client):
    with client.websocket_connect("/v1/asr/stream?language=zh") as websocket:
        started = websocket.receive_json()
        assert started["event"] == "started"
        websocket.send_bytes(b"chunk-one")
        partial = websocket.receive_json()
        assert partial["event"] == "result"
        assert partial["is_final"] is False
        websocket.send_text("__end__")
        final = websocket.receive_json()
        assert final["event"] == "result"
        assert final["is_final"] is True
