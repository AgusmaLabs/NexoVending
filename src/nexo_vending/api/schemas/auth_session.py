"""HTTP DTOs for session facade and operator bootstrap."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IssueSessionRequest(BaseModel):
    id_token: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)


class SessionOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class OperatorOut(BaseModel):
    operator_id: str
    tenant_id: str
    role: str
    status: str
    display_name: str | None = None
    email: str | None = None
    provider: str
    subject: str
