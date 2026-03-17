"""Munshi entry point — starts the voice assistant and optional API server."""

import asyncio
import sys

from loguru import logger

from munshi.config import settings
from munshi.db.database import init_db


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    logger.add(
        "logs/munshi.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )


async def run_voice_assistant() -> None:
    """Run the voice assistant loop."""
    from munshi.core.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    await orchestrator.run()


async def run_api_server() -> None:
    """Run the FastAPI REST server."""
    import uvicorn

    from munshi.api.server import create_app

    app = create_app()
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main_async() -> None:
    configure_logging()

    # Ensure DB and data dirs exist
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    import os
    os.makedirs("logs", exist_ok=True)

    logger.info(f"Starting Munshi v{__import__('munshi').__version__}")
    logger.info(f"Shop: {settings.shop_name} | Language: {settings.shop_language}")

    await init_db()
    logger.info("Database initialised")

    # Run voice assistant and API server concurrently
    await asyncio.gather(
        run_voice_assistant(),
        run_api_server(),
    )


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Munshi stopped.")


if __name__ == "__main__":
    main()
