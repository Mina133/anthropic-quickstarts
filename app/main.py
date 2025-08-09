import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers.sessions import router as sessions_router
from .routers.messages import router as messages_router
from .routers.stream import router as stream_router
from .routers.vnc import router as vnc_router


settings = get_settings()


def create_app() -> FastAPI:
    # Create tables on startup (simple for demo; use migrations in prod)
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(stream_router)
    app.include_router(vnc_router)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)


