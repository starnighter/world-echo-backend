from typing import Any


def success_response(data: Any = None, message: str = "success", code: int = 0) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def error_response(message: str, code: int) -> dict[str, Any]:
    return {"code": code, "message": message, "data": None}
