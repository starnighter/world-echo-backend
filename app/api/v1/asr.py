from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.core.responses import success_response
from app.db.models import User
from app.schemas.asr import ASRTranscribeResponse
from app.services.asr_service import ASRService


router = APIRouter()
settings = get_settings()
asr_service = ASRService(settings)


@router.post("/transcribe")
async def transcribe(
    _: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in {"mp3", "wav", "m4a", "ogg"}:
        raise BadRequestException("Unsupported audio format")
    content = await file.read()
    if len(content) > settings.upload_audio_max_mb * 1024 * 1024:
        raise BadRequestException("File too large")
    payload = await asr_service.transcribe(content, file.filename or "audio", language)
    return success_response(ASRTranscribeResponse(**payload).model_dump())


@router.websocket("/stream")
async def stream_transcribe(websocket: WebSocket):
    await websocket.accept()
    language = websocket.query_params.get("language", "zh")
    try:
        await asr_service.bridge_stream(websocket, language=language)
    except WebSocketDisconnect:
        return
    finally:
        await websocket.close()
