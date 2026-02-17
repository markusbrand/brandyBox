"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.db.session import get_session, init_db
from app.files.routes import router as files_router
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

app.include_router(users_router)
app.include_router(files_router)


@app.get("/health")
@limiter.exempt
def health() -> JSONResponse:
    """Health check for Docker and tunnel. Exempt from rate limiting."""
    return JSONResponse(content={"status": "ok"})
