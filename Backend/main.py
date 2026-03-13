"""
Main FastAPI application — production-grade entry point.
Wires all routers, middleware, startup/shutdown lifecycle.
"""
import os
import sys

# Ensure Backend/ is on sys.path when running 'uvicorn main:app'
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import create_tables
from core.logging_config import setup_logging, logger

# ── App init ──────────────────────────────────────────────────────────────────
setup_logging(debug=settings.DEBUG)

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade AI Research Assistant with hybrid RAG, multi-agent orchestration, and citation-aware responses.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting (slowapi, optional — requires Redis) ────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    _storage_uri = settings.REDIS_URL if settings.REDIS_ENABLED else "memory://"
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=_storage_uri,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiter enabled", storage=_storage_uri)
except ImportError:
    logger.warning("slowapi not installed — rate limiting disabled")

# ── Routers ───────────────────────────────────────────────────────────────────
from api.routes.auth import router as auth_router
from api.routes.documents import router as documents_router
from api.routes.query import router as query_router
from api.routes.agents import router as agents_router

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(agents_router)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Starting up AI Research Assistant")

    # Create DB tables
    await create_tables()
    logger.info("Database tables created/verified")

    # Pre-load FAISS + BM25 from existing chunks
    try:
        from services.retrieval.hybrid import rebuild_index_from_db
        await rebuild_index_from_db()
        logger.info("Vector index rebuilt from DB")
    except Exception as e:
        logger.warning("Could not rebuild index on startup", error=str(e))

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down AI Research Assistant")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "llm_model": settings.LLM_MODEL,
        "embed_model": settings.EMBED_MODEL,
        "redis_enabled": settings.REDIS_ENABLED,
        "celery_enabled": settings.CELERY_ENABLED,
    }


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
