from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.responses import error_response, success_response
from app.db.init_db import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.static_root.mkdir(parents=True, exist_ok=True)
app.mount(settings.static_url, StaticFiles(directory=settings.static_root), name="static")


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.message, exc.code))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = exc.status_code if exc.status_code in {400, 401, 403, 404, 409, 422, 429, 500} else 500
    return JSONResponse(status_code=exc.status_code, content=error_response(str(exc.detail), code))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=error_response(str(exc.errors()), 422))


@app.get("/health")
async def health() -> dict:
    return success_response({"status": "ok"})


app.include_router(api_router, prefix=settings.api_v1_prefix)
