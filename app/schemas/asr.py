from pydantic import BaseModel


class ASRTranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float
