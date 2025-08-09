from fastapi import APIRouter
from ..config import get_settings


router = APIRouter(prefix="/vnc", tags=["vnc"])
settings = get_settings()


@router.get("/info")
def vnc_info():
    return {
        "novnc_url": f"http://localhost:{settings.novnc_port}/vnc.html",
        "vnc_host": settings.vnc_host,
        "vnc_port": settings.vnc_port,
    }


