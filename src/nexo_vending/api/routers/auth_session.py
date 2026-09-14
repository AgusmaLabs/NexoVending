"""Session facade + operator bootstrap HTTP adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from nexo_platform.identity import AuthenticationError, InvalidCredentialsError
from nexo_platform.tenant import RequestContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.auth import get_request_context
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.api.dependencies.wiring import run_query
from nexo_vending.api.schemas.auth_session import (
    IssueSessionRequest,
    OperatorOut,
    SessionOut,
)
from nexo_vending.application.identity.get_current_operator import GetCurrentOperatorQuery
from nexo_vending.application.identity.issue_session import IssueOperatorSessionCommand
from nexo_vending.config import settings
from nexo_vending.domain.identity.errors import OperatorNotFoundError

router = APIRouter(tags=["auth"])


@router.post("/auth/session", response_model=SessionOut)
async def issue_session(
    body: IssueSessionRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict:
    provider = getattr(request.app.state, "authentication_provider", None)
    jwt_service = getattr(request.app.state, "jwt_service", None)
    if provider is None or jwt_service is None:
        raise HTTPException(status_code=503, detail="authentication not configured")

    async def _handler(factory):
        try:
            token = await factory.issue_operator_session(
                authentication=provider,
                jwt_service=jwt_service,
            ).execute(
                IssueOperatorSessionCommand(
                    id_token=body.id_token,
                    tenant_id=body.tenant_id,
                    expires_in=settings.jwt_expires_in,
                )
            )
        except OperatorNotFoundError:
            raise
        except (InvalidCredentialsError, AuthenticationError) as exc:
            raise HTTPException(status_code=401, detail=str(exc) or "invalid credentials") from exc
        return SessionOut(
            access_token=token.access_token,
            token_type="Bearer",
            expires_in=token.expires_in,
        ).model_dump()

    return await run_query(session, _handler)


@router.get("/operators/me", response_model=OperatorOut)
async def get_current_operator(
    session: Session = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> dict:
    async def _handler(factory):
        operator = await factory.get_current_operator().execute(
            GetCurrentOperatorQuery(context=context)
        )
        email = str(operator.email.value) if operator.email is not None else None
        return OperatorOut(
            operator_id=str(operator.id.value),
            tenant_id=str(operator.tenant_id.value),
            role=operator.role.value,
            status=operator.status.value,
            display_name=operator.display_name,
            email=email,
            provider=operator.principal.provider,
            subject=operator.principal.subject,
        ).model_dump()

    return await run_query(session, _handler)
