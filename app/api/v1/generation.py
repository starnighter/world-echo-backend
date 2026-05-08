from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import BadRequestException, UnprocessableException
from app.core.responses import success_response
from app.db.models import User
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.song import ImageGenerateRequest, PromptGenerateRequest, VoiceGenerateRequest
from app.services.asr_service import ASRService
from app.services.audio_analysis_service import AudioAnalysisService
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
    cleanup_message = "Song generation stream ended unexpectedly"
    try:
        async for chunk in music_service.stream_generate(
            model=model_used,
            prompt=final_prompt,
            lyrics=lyrics,
            is_instrumental=is_instrumental,
            audio_url=source_url if source_type == "voice" and model_used.startswith("music-cover") else None,
        ):
            payload = {
                "status": chunk.status,
                "audio_hex": chunk.audio_hex,
                "extra_info": chunk.extra_info if chunk.status == 2 else None,
                "song": None,
            }
            if chunk.status == 1:
                yield _sse_line(success_response(payload))
            elif chunk.status == 2:
                final_audio_hex = chunk.audio_hex or ""
                final_extra = chunk.extra_info

        music_url = storage_service.save_bytes(bytes.fromhex(final_audio_hex), "generated/music", "mp3")
        cover_url = str(random.randint(1, 8))
        song = await song_service.complete_song(
            db,
            song,
            music_url=music_url,
            cover_url=cover_url,
            title=(prompt or final_prompt)[:50] or "Untitled",
            description=(final_prompt[:200] if final_prompt else None),
            extracted_data=extracted_data,
        )
        payload = {
            "status": 2,
            "audio_hex": final_audio_hex,
            "extra_info": final_extra,
            "song": song_service.to_detail(song).model_dump(mode="json"),
        }
        yield _sse_line(success_response(payload))
        cleanup_message = ""
    except (asyncio.CancelledError, GeneratorExit):
        cleanup_message = "Song generation stream cancelled by client disconnect"
        raise
    except Exception as exc:
        cleanup_message = str(exc)
        await song_service.fail_song(db, song, str(exc))
        yield _sse_line({"code": 500, "message": str(exc), "data": {"status": 3, "audio_hex": None, "extra_info": None, "song": None}})
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
    asr_result = await asr_service.transcribe(audio_path.read_bytes(), audio_path.name, language="zh")
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
    model_used = payload.model_used or "music-cover"
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
    )
    return StreamingResponse(stream, media_type="text/event-stream")
