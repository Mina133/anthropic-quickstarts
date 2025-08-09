from fastapi import APIRouter
from ..config import get_settings


router = APIRouter(prefix="/vnc", tags=["vnc"])
settings = get_settings()


@router.get("/info")
def vnc_info():
    # Deprecated: with per-session VMs, the frontend should read novnc_port from the session metadata
    return {
        "novnc_url": f"http://localhost:{settings.novnc_port}/vnc.html",
        "vnc_host": settings.vnc_host,
        "vnc_port": settings.vnc_port,
    }


