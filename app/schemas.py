from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ThesisCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    advisor_id: int | None = None


class ThesisUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    advisor_id: int | None = None


class ReturnRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class AssignItem(BaseModel):
    thesis_id: int
    reviewer_ids: list[int] = Field(min_length=1)
    reason: str | None = None


class AssignRequest(BaseModel):
    items: list[AssignItem] = Field(min_length=1)
    due_at: datetime | None = None


class AutoAssignRequest(BaseModel):
    reviewers_per_thesis: int = Field(default=2, ge=1, le=5)
    max_task_limit: int = Field(default=8, ge=1, le=50)
    reason: str | None = None


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


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ReviewerCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=64)


class ReviewerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=64)


class ReviewerResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class StudentCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    student_no: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)


class StudentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    student_no: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)


class StudentResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)
