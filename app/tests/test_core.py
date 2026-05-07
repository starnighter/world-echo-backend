from app.core.responses import error_response, success_response
from app.core.security import create_access_token, decode_access_token


def test_success_response_shape():
    payload = success_response({"ok": True})
    assert payload == {"code": 0, "message": "success", "data": {"ok": True}}


def test_error_response_shape():
    payload = error_response("bad", 400)
    assert payload == {"code": 400, "message": "bad", "data": None}


def test_jwt_roundtrip():
    token = create_access_token("12345678-1234-5678-1234-567812345678")
    payload = decode_access_token(token)
    assert payload["sub"] == "12345678-1234-5678-1234-567812345678"
