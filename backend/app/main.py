from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.auth import users_router
from app.api.observations import router as observations_router
from app.api.reports import router as reports_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine, ping_database
from app.services.auth import AuthService


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if settings.should_create_schema:
        Base.metadata.create_all(bind=engine)
    if settings.should_bootstrap_dev_users:
        db = SessionLocal()
        try:
            AuthService(db).ensure_dev_admin()
            print(
                "AOP bootstrap ready — login with "
                f"{settings.dev_admin_username}/{settings.dev_admin_password} "
                "or umair/" + settings.dev_admin_password,
                flush=True,
            )
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
        payload = {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "db_backend": settings.db_backend,
        }
        if settings.health_check_db:
            db = SessionLocal()
            try:
                ping_database(db)
                payload["database"] = "up"
            except Exception:
                payload["status"] = "degraded"
                payload["database"] = "down"
            finally:
                db.close()
        return payload

    @app.get("/ready")
    def ready():
        """Readiness: requires DB connectivity (for load balancers)."""
        db = SessionLocal()
        try:
            ping_database(db)
            if settings.db_backend.lower() == "oracle":
                # Confirm CURRENT_SCHEMA / grants by probing a core object
                db.execute(text("SELECT 1 FROM users WHERE ROWNUM = 1"))
            return {"status": "ready"}
        except Exception as exc:
            return {"status": "not_ready", "detail": str(exc.__class__.__name__)}
        finally:
            db.close()

    return app


app = create_app()
