from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.auth import users_router
from app.api.observations import router as observations_router
from app.api.reports import router as reports_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.services.auth import AuthService


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        AuthService(db).ensure_dev_admin()
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Enterprise Audit Observations Platform API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(observations_router, prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    return app


app = create_app()
