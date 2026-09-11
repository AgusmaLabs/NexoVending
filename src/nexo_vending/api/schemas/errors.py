"""Stable HTTP error envelope."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody = Field(...)
