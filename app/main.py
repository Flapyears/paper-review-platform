from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_settings
from app.database import create_engine_and_session, create_tables
from app.routers import admin, files, reviewer, student


def create_app(
    database_url: str | None = None,
    storage_dir: str | None = None,
    max_upload_size: int | None = None,
) -> FastAPI:
    app = FastAPI(title="Paper Review Platform", version="0.1.0")

    settings = load_settings(
        database_url=database_url, storage_dir=storage_dir, max_upload_size=max_upload_size
    )
    engine, session_local = create_engine_and_session(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_local = session_local
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    create_tables(engine)

    app.include_router(student.router)
    app.include_router(admin.router)
    app.include_router(reviewer.router)
    app.include_router(files.router)

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
