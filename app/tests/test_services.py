import asyncio
from pathlib import Path

from app.services.music_generation_service import GeneratedChunk


async def _collect_chunks(service):
    result = []
    async for chunk in service.stream_generate(
        model="music-2.6",
        prompt="warm pop",
        lyrics="hello",
        is_instrumental=False,
    ):
        result.append(chunk)
    return result


def test_storage_service_save_bytes(storage_service):
    url = storage_service.save_bytes(b"abc", "generated/music", "mp3")
    assert url.startswith("/static/generated/music/")
    file_path = storage_service.resolve_local_path(url)
    assert file_path.read_bytes() == b"abc"


def test_mock_asr_transcribe(asr_service):
    result = asyncio.run(asr_service.transcribe(b"hello world", "sample.wav", "zh"))
    assert result["language"] == "zh"
    assert "sample.wav" in result["text"]


def test_mock_music_generation_stream(music_generation_service):
    chunks = asyncio.run(_collect_chunks(music_generation_service))
    assert len(chunks) == 4
    assert all(isinstance(chunk, GeneratedChunk) for chunk in chunks)
    assert chunks[-1].status == 2
    assert chunks[-1].extra_info["sample_rate"] == 44100
