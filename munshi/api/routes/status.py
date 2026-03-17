"""Status and health check routes."""

import platform
from datetime import datetime

from fastapi import APIRouter

from munshi.config import settings

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_status():
    return {
        "status": "ok",
        "version": __import__("munshi").__version__,
        "shop": settings.shop_name,
        "timestamp": datetime.now().isoformat(),
        "platform": platform.machine(),
        "cloud_sync": settings.cloud_sync_enabled,
        "claude_model": settings.claude_model,
        "language": settings.shop_language,
    }
