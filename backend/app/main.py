"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.db.session import get_session, init_db
from app.files.hash_model import FileHash  # noqa: F401  # register for create_all
from app.files.routes import router as files_router
from app.meta.routes import router as meta_router
from app.oauth.routes import router as oauth_router
from app.telemetry.routes import router as telemetry_router
from app.users.routes import router as users_router
from app.users.service import ensure_admin_exists

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure logging from settings (stderr always; optional file)."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger("app")
    root.setLevel(level)
    root.handlers.clear()
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if settings.log_file and str(settings.log_file).strip():
        try:
            fh = logging.FileHandler(settings.log_file, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(fmt)
            root.addHandler(fh)
            root.info("Logging to file %s", settings.log_file)
        except OSError as e:
            root.warning("Could not open log file %s: %s", settings.log_file, e)
    else:
        root.debug("Logging to stderr only (no log_file set)")


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and bootstrap admin on startup."""
    log.info("Startup: initializing database and admin")
    await init_db()
    async with get_session() as session:
        await ensure_admin_exists(session)
    log.info("Startup complete")
    yield
    log.info("Shutdown")


app = FastAPI(title="Brandy Box API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Return generic 500 without leaking stack trace or internals."""
    if isinstance(exc, HTTPException):
        raise exc
    log.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

from app.limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/health")
@limiter.exempt
def health() -> JSONResponse:
    """Health check for Docker and tunnel. Exempt from rate limiting."""
    return JSONResponse(content={"status": "ok"})


app.include_router(users_router)
app.include_router(oauth_router)
app.include_router(meta_router)
app.include_router(telemetry_router)
app.include_router(files_router)

_spa_root: Path | None = None
_static_settings = get_settings()
if _static_settings.static_dist_path:
    _sr = Path(_static_settings.static_dist_path).resolve()
    if _sr.is_dir() and (_sr / "index.html").is_file():
        _spa_root = _sr
        _assets = _sr / "assets"
        if _assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(_assets)), name="spa_assets")
        log.info("Serving web SPA from %s (assets under /assets)", _sr)


def _spa_index_response() -> FileResponse:
    if not _spa_root:
        raise HTTPException(status_code=404, detail="Web UI not configured")
    idx = _spa_root / "index.html"
    if not idx.is_file():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(idx)


@app.get("/")
@limiter.exempt
async def spa_root() -> FileResponse:
    """Serve SPA for root (Vite build)."""
    return _spa_index_response()


@app.get("/{path:path}")
@limiter.exempt
async def spa_or_asset(path: str) -> FileResponse:
    """
    Serve hashed assets from dist/ or SPA index.html for client routes (/login, /files, …).
    API routes under /api are handled by routers registered above.
    """
    if not _spa_root:
        raise HTTPException(status_code=404, detail="Not found")
    if path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")
    if path in ("openapi.json", "docs", "redoc") or path.startswith("docs/") or path.startswith("redoc/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = (_spa_root / path).resolve()
    try:
        candidate.relative_to(_spa_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None
    if candidate.is_file():
        return FileResponse(candidate)
    return _spa_index_response()
