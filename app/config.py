from dataclasses import dataclass
import os


@dataclass
class Settings:
    database_url: str = "sqlite:///./paper_review.db"
    storage_dir: str = "./storage"
    max_upload_size: int = 20 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx")
    max_reviewers_per_department: int = 1


def load_settings(
    database_url: str | None = None,
    storage_dir: str | None = None,
    max_upload_size: int | None = None,
    max_reviewers_per_department: int | None = None,
) -> Settings:
    return Settings(
        database_url=database_url or os.getenv("DATABASE_URL", "sqlite:///./paper_review.db"),
        storage_dir=storage_dir or os.getenv("STORAGE_DIR", "./storage"),
        max_upload_size=max_upload_size
        if max_upload_size is not None
        else int(os.getenv("MAX_UPLOAD_SIZE", str(20 * 1024 * 1024))),
        max_reviewers_per_department=max_reviewers_per_department
        if max_reviewers_per_department is not None
        else int(os.getenv("MAX_REVIEWERS_PER_DEPARTMENT", "1")),
    )
