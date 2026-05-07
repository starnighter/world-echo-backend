import asyncio

from app.api.v1.generation import _sse_line
from app.core.responses import success_response


def test_sse_line_format():
    line = _sse_line(success_response({"status": 1, "audio_hex": "abcd", "extra_info": None, "song": None}))
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
