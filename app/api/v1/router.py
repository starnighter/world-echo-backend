from fastapi import APIRouter

from app.api.v1 import asr, auth, favorites, generation, playlists, plaza, songs, upload


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(asr.router, prefix="/asr", tags=["ASR"])
api_router.include_router(generation.router, prefix="/songs/generate", tags=["Generation"])
api_router.include_router(songs.router, prefix="/songs", tags=["Songs"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["Playlists"])
api_router.include_router(plaza.router, prefix="/plaza", tags=["Plaza"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
