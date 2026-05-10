from __future__ import annotations

import asyncio
import json
import random
import re
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import AppException, BadRequestException, UnprocessableException
from app.core.responses import success_response
from app.db.models import User
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.song import ImageGenerateRequest, PromptGenerateRequest, VoiceGenerateRequest
from app.services.asr_service import ASRService
from app.services.audio_analysis_service import AudioAnalysisService
from app.services.lyrics_generation_service import LyricsGenerationService
from app.services.music_generation_service import MusicGenerationService
from app.services.prompt_refiner_service import PromptRefinerService
from app.services.song_service import SongService
from app.services.storage_service import StorageService
from app.services.vision_prompt_service import VisionPromptService


router = APIRouter()
settings = get_settings()
song_service = SongService()
storage_service = StorageService(settings)
vision_service = VisionPromptService(settings)
audio_analysis_service = AudioAnalysisService(settings)
music_service = MusicGenerationService(settings)
lyrics_service = LyricsGenerationService(settings)
asr_service = ASRService(settings)
prompt_refiner_service = PromptRefinerService(settings)


def _ensure_sse_accept(accept: str | None) -> None:
    if accept is None or "text/event-stream" not in accept:
        raise BadRequestException("Accept header must be text/event-stream")


def _ensure_generation_user_allowed(user: User) -> None:
    if user.is_banned:
        raise UnprocessableException("User has been banned")


def _sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _generation_event(
    *,
    song_id: str,
    status: int,
    phase: str,
    message: str | None = None,
    progress: float | None = None,
    extra_info: dict | None = None,
) -> dict:
    return success_response(
        {
            "status": status,
            "song_id": song_id,
            "phase": phase,
            "progress": progress,
            "message": message,
            "extra_info": extra_info,
        }
    )


def _derive_song_title(*, prompt: str | None, final_prompt: str, source_type: str) -> str:
    raw = (prompt or final_prompt or "").strip()
    if not raw:
        return "未命名歌曲"

    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    first_sentence = re.split(r"[。！？!?；;,.，]", first_line, maxsplit=1)[0].strip()
    title = first_sentence or first_line
    title = re.sub(
        r"^(请你?|帮我|麻烦你?)?\s*(根据[^，,。.!！?？；;]*?)?(生成|创作|制作|写|做)(一首|一段)?",
        "",
        title,
    ).strip()
    title = re.sub(r"\s+", " ", title)
    title = title.strip(" -_：:，,。.!！?？\"'“”‘’")
    if len(title) < 2:
        title = "未命名歌曲"
    if len(title) <= 32:
        return title
    truncated = title[:32].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated or title[:32] or "未命名歌曲"


async def _stream_song_generation(
    *,
    db: AsyncSession,
    user: User,
    source_type: str,
    source_url: str | None,
    prompt: str | None,
    lyrics: str | None,
    is_instrumental: bool,
    model_used: str,
    extracted_data: dict | None,
    final_prompt: str,
    generated_title: str | None = None,
) -> AsyncIterator[str]:
    song = await song_service.create_generation_song(
        db,
        user=user,
        source_type=source_type,
        source_url=source_url,
        prompt=prompt,
        lyrics=lyrics,
        is_instrumental=is_instrumental,
        model_used=model_used,
    )
    await song_service.mark_processing(db, song)

    final_audio_hex = ""
    final_extra = None
    resolved_title = generated_title
    generation_lyrics = lyrics
    cleanup_message = "Song generation stream ended unexpectedly"
    try:
        yield _sse_line(
            _generation_event(
                song_id=str(song.id),
                status=1,
                phase="queued",
                progress=0.05,
                message="Generation queued",
            )
        )
        if not is_instrumental and not generation_lyrics:
            yield _sse_line(
                _generation_event(
                    song_id=str(song.id),
                    status=1,
                    phase="writing_lyrics",
                    progress=0.12,
                    message="Generating lyrics and title",
                )
            )
            lyrics_result = await lyrics_service.generate_full_song(
                prompt=final_prompt,
            )
            generation_lyrics = lyrics_result.lyrics
            resolved_title = lyrics_result.song_title or resolved_title
            extracted_data = {
                **(extracted_data or {}),
                "lyrics_generation": {
                    "song_title": lyrics_result.song_title,
                    "style_tags": lyrics_result.style_tags,
                },
            }

        yield _sse_line(
            _generation_event(
                song_id=str(song.id),
                status=1,
                phase="generating",
                progress=0.2,
                message="Generating audio",
            )
        )
        async for chunk in music_service.stream_generate(
            model=model_used,
            prompt=final_prompt,
            lyrics=generation_lyrics,
            is_instrumental=is_instrumental,
        ):
            if chunk.status == 1:
                yield _sse_line(
                    _generation_event(
                        song_id=str(song.id),
                        status=1,
                        phase="generating",
                        progress=0.65,
                        message="Generating audio",
                    )
                )
            elif chunk.status == 2:
                final_audio_hex = chunk.audio_hex or ""
                final_extra = chunk.extra_info
        if not final_audio_hex:
            raise UnprocessableException("No audio generated")
        try:
            final_audio = bytes.fromhex(final_audio_hex)
        except ValueError as exc:
            raise UnprocessableException("Invalid generated audio") from exc
        try:
            final_audio = storage_service.normalize_mp3_payload(final_audio)
        except AppException as exc:
            raise UnprocessableException(exc.message) from exc

        yield _sse_line(
            _generation_event(
                song_id=str(song.id),
                status=1,
                phase="finalizing",
                progress=0.9,
                message="Finalizing song",
                extra_info=final_extra,
            )
        )
        music_url = storage_service.save_bytes(final_audio, "generated/music", "mp3")
        cover_url = str(random.randint(1, 8))
        song = await song_service.complete_song(
            db,
            song,
            music_url=music_url,
            cover_url=cover_url,
            title=resolved_title or _derive_song_title(
                prompt=prompt,
                final_prompt=final_prompt,
                source_type=source_type,
            ),
            description=(final_prompt[:200] if final_prompt else None),
            extracted_data=extracted_data,
            lyrics=generation_lyrics,
        )
        yield _sse_line(
            _generation_event(
                song_id=str(song.id),
                status=2,
                phase="completed",
                progress=1.0,
                message="Song generated successfully",
                extra_info=final_extra,
            )
        )
        cleanup_message = ""
    except (asyncio.CancelledError, GeneratorExit):
        cleanup_message = "Song generation stream cancelled by client disconnect"
        raise
    except Exception as exc:
        cleanup_message = str(exc)
        await song_service.fail_song(db, song, str(exc))
        yield _sse_line(
            {
                "code": 500,
                "message": str(exc),
                "data": {
                    "status": 3,
                    "song_id": str(song.id),
                    "phase": "failed",
                    "progress": None,
                    "message": str(exc),
                    "extra_info": None,
                },
            }
        )
    finally:
        if cleanup_message and song.status == "processing":
            async with AsyncSessionLocal() as cleanup_db:
                await song_service.fail_song_if_processing(cleanup_db, song.id, cleanup_message)


@router.post("/prompt")
async def generate_prompt_song(
    payload: PromptGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    accept: str | None = Header(default=None),
):
    _ensure_sse_accept(accept)
    _ensure_generation_user_allowed(current_user)
    model_used = payload.model_used or "music-2.6"
    stream = _stream_song_generation(
        db=db,
        user=current_user,
        source_type="prompt",
        source_url=None,
        prompt=payload.prompt,
        lyrics=payload.lyrics,
        is_instrumental=payload.is_instrumental,
        model_used=model_used,
        extracted_data={"prompt_mode": True},
        final_prompt=payload.prompt,
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/image")
async def generate_image_song(
    payload: ImageGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    accept: str | None = Header(default=None),
):
    _ensure_sse_accept(accept)
    _ensure_generation_user_allowed(current_user)
    image_path = await storage_service.materialize_source(
        payload.source_url,
        category="remote/images",
        default_extension="png",
        max_size_mb=settings.upload_image_max_mb,
    )
    analysis = await vision_service.analyze_image(image_path, payload.prompt)
    final_prompt = analysis.get("style_prompt") or payload.prompt or "cinematic soundtrack"
    model_used = payload.model_used or "music-2.6"
    stream = _stream_song_generation(
        db=db,
        user=current_user,
        source_type="image",
        source_url=payload.source_url,
        prompt=payload.prompt,
        lyrics=payload.lyrics,
        is_instrumental=payload.is_instrumental,
        model_used=model_used,
        extracted_data=analysis,
        final_prompt=final_prompt,
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/voice")
async def generate_voice_song(
    payload: VoiceGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    accept: str | None = Header(default=None),
):
    _ensure_sse_accept(accept)
    _ensure_generation_user_allowed(current_user)
    audio_path = await storage_service.materialize_source(
        payload.source_url,
        category="remote/audio",
        default_extension="m4a",
        max_size_mb=settings.upload_audio_max_mb,
    )
    analysis = await audio_analysis_service.analyze(audio_path)
    asr_result = await asr_service.transcribe(
        audio_path.read_bytes(),
        audio_path.name,
        language="zh",
    )
    analysis["asr_text"] = asr_result["text"]
    refined = await prompt_refiner_service.refine_from_audio_features(
        audio_features=analysis,
        asr_text=asr_result["text"],
        extra_prompt=payload.prompt,
        spectrogram_path=Path(analysis["spectrogram_path"]) if analysis.get("spectrogram_path") else None,
    )
    analysis["prompt_refinement"] = refined
    final_prompt = refined.get("style_prompt") or ", ".join(
        [
            payload.prompt or "",
            f"bpm {analysis.get('bpm')}",
            f"genre {'/'.join(analysis.get('genre', []))}",
            f"tags {'/'.join(analysis.get('tags', []))}",
            asr_result["text"],
        ]
    ).strip(", ")
    refined_title = (refined.get("song_title") or "").strip()
    model_used = "music-2.6"
    stream = _stream_song_generation(
        db=db,
        user=current_user,
        source_type="voice",
        source_url=payload.source_url,
        prompt=payload.prompt,
        lyrics=payload.lyrics,
        is_instrumental=payload.is_instrumental,
        model_used=model_used,
        extracted_data=analysis,
        final_prompt=final_prompt,
        generated_title=refined_title or None,
    )
    return StreamingResponse(stream, media_type="text/event-stream")
