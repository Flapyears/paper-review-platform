from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ThesisCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    advisor_id: int | None = None


class ThesisUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ReturnRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class AssignItem(BaseModel):
    thesis_id: int
    reviewer_ids: list[int] = Field(min_length=1)
    reason: str | None = None


class AssignRequest(BaseModel):
    items: list[AssignItem] = Field(min_length=1)
    due_at: datetime | None = None


class ReplaceRequest(BaseModel):
    new_reviewer_id: int
    reason: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


class ReviewFormDraftRequest(BaseModel):
    score: int | None = Field(default=None, ge=0, le=100)
    grade: str | None = None
    allow_defense: str | None = None
    comments: str | None = None
    internal_comments: str | None = None


class MessageResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None

