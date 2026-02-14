from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import load_settings
from app.database import create_engine_and_session, create_tables, run_compat_migrations
from app.routers import admin, auth, dev, files, reviewer, student
from app.services.auth import seed_default_accounts


def create_app(
    database_url: str | None = None,
    storage_dir: str | None = None,
    max_upload_size: int | None = None,
    max_reviewers_per_department: int | None = None,
) -> FastAPI:
    app = FastAPI(title="Paper Review Platform", version="0.1.0")

    settings = load_settings(
        database_url=database_url,
        storage_dir=storage_dir,
        max_upload_size=max_upload_size,
        max_reviewers_per_department=max_reviewers_per_department,
    )
    engine, session_local = create_engine_and_session(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_local = session_local
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    create_tables(engine)
    run_compat_migrations(engine)
    with Session(bind=engine) as db:
        seed_default_accounts(db)

    app.include_router(auth.router)
    app.include_router(student.router)
    app.include_router(admin.router)
    app.include_router(reviewer.router)
    app.include_router(files.router)
    if settings.enable_dev_endpoints:
        app.include_router(dev.router)

    frontend_dist = Path("frontend/dist")
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        if (frontend_dist / "index.html").exists():
            return FileResponse(str(frontend_dist / "index.html"))
        raise HTTPException(status_code=404, detail="Frontend not built yet.")

    @app.get("/{path:path}")
    def spa_fallback(path: str) -> FileResponse:  # noqa: ARG001
        if (frontend_dist / "index.html").exists():
            return FileResponse(str(frontend_dist / "index.html"))
        raise HTTPException(status_code=404, detail="Route not found.")

    return app


app = create_app()
