"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from munshi.api.routes import inventory, ledger, status, udhar
from munshi.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Munshi API",
        description="Voice-first AI assistant for kirana stores",
        version=__import__("munshi").__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Allow local companion app / web dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Simple API key auth middleware
    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        # Skip auth for docs and health check
        if request.url.path in ("/docs", "/redoc", "/openapi.json", "/status"):
            return await call_next(request)
        key = request.headers.get("X-Munshi-Key", "")
        if settings.api_key and key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
        return await call_next(request)

    app.include_router(status.router)
    app.include_router(ledger.router, prefix="/api/v1")
    app.include_router(udhar.router, prefix="/api/v1")
    app.include_router(inventory.router, prefix="/api/v1")

    return app
