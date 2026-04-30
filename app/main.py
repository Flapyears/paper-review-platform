from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import load_settings
from app.database import create_engine_and_session, create_tables, run_compat_migrations
from app.routers import admin, auth, dev, files, reviewer, student
from app.services.auth import seed_default_accounts, seed_demo_accounts as seed_demo_accounts_data


def create_app(
    database_url: str | None = None,
    storage_dir: str | None = None,
    max_upload_size: int | None = None,
    max_reviewers_per_department: int | None = None,
    seed_demo_accounts: bool = False,
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
        if seed_demo_accounts:
            seed_demo_accounts_data(db)
        else:
            seed_default_accounts(db)

    app.include_router(auth.router)
    app.include_router(student.router)
    app.include_router(admin.router)
    app.include_router(reviewer.router)
    app.include_router(files.router)
    if settings.enable_dev_endpoints:
        app.include_router(dev.router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_msgs = []
        # 中文映射表
        field_map = {
            "username": "用户名",
            "password": "密码",
            "name": "姓名",
            "title": "标题",
            "advisor_id": "指导教师",
            "student_no": "学号",
            "email": "电子邮箱",
            "department": "所属部门",
            "reason": "原因/意见",
            "score": "评分",
        }
        
        for error in exc.errors():
            loc = error["loc"][-1]
            field_name = field_map.get(loc, loc)
            msg = error["msg"]
            
            # 翻译常见错误类型
            if error["type"] == "string_too_short":
                min_len = error["ctx"].get("min_length")
                msg = f"长度不能少于 {min_len} 个字符"
            elif error["type"] == "string_too_long":
                max_len = error["ctx"].get("max_length")
                msg = f"长度不能超过 {max_len} 个字符"
            elif error["type"] == "value_error.missing":
                msg = "不能为空"
            elif error["type"] == "type_error.integer":
                msg = "必须为整数"
            
            error_msgs.append(f"【{field_name}】{msg}")
            
        return JSONResponse(
            status_code=422,
            content={"detail": "，".join(error_msgs)},
        )

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
