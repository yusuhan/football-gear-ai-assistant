"""HTTP routes for the Football Gear AI Assistant."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.security import Operator, require_admin, require_operator
from app.models.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AuditLogResponse,
    ChatRequest,
    ChatResponse,
    ChannelMessageRequest,
    ChannelMessageResponse,
    HealthResponse,
    HandoffTicketRecordResponse,
    HandoffTicketUpdateRequest,
    InventoryResponse,
    MessageRecordResponse,
    OperationsSessionResponse,
    OperationsUserCreateRequest,
    OperationsUserResponse,
    OperationsUserUpdateRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    ProductResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return basic runtime status for local and deployment checks."""

    repository = request.app.state.repository
    conversation_repository = request.app.state.conversation_repository
    faq_knowledge_base = request.app.state.faq_knowledge_base
    return HealthResponse(
        status="ok",
        products=repository.count_products(),
        inventory_rows=repository.count_inventory_rows(),
        faq_articles=faq_knowledge_base.article_count,
        conversations=conversation_repository.count_conversations(),
        open_handoffs=conversation_repository.count_open_handoffs(),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Answer a customer support question."""

    conversation_service = request.app.state.conversation_service
    return conversation_service.handle_chat(payload)


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Stream the answer text for the chat frontend."""

    conversation_service = request.app.state.conversation_service
    response = conversation_service.handle_chat(payload)

    def generate_answer():
        for index in range(0, len(response.answer), 12):
            yield response.answer[index : index + 12]

    return StreamingResponse(
        generate_answer(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Conversation-Id": response.conversation_id or ""},
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
def chat_v1(payload: ChatRequest, request: Request) -> ChatResponse:
    """Versioned alias for clients that prefer an explicit API prefix."""

    return chat(payload, request)


@router.post("/channels/{channel}/messages", response_model=ChannelMessageResponse)
def receive_channel_message(
    channel: str,
    payload: ChannelMessageRequest,
    request: Request,
) -> ChannelMessageResponse:
    """Receive a normalized inbound message from an external channel."""

    channel_adapter_service = request.app.state.channel_adapter_service
    return channel_adapter_service.handle_message(channel, payload)


@router.get("/products", response_model=list[ProductResponse])
def list_products(request: Request) -> list[ProductResponse]:
    """Return demo product catalog."""

    repository = request.app.state.repository
    return [ProductResponse(**product) for product in repository.list_products()]


@router.get("/inventory", response_model=list[InventoryResponse])
def list_inventory(request: Request) -> list[InventoryResponse]:
    """Return demo inventory rows."""

    repository = request.app.state.repository
    return [InventoryResponse(**row) for row in repository.list_inventory()]


@router.post("/admin/auth/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, request: Request) -> AdminLoginResponse:
    """Create a short-lived operations session from username and password."""

    operations_repository = request.app.state.operations_repository
    session = operations_repository.authenticate(payload.username, payload.password)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin credentials")
    operations_repository.create_audit_log(
        session["operator"],
        action="operations.login",
        resource_type="session",
        details={"expires_at": session["expires_at"]},
    )
    return AdminLoginResponse(**session)


@router.post("/admin/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def admin_logout(
    request: Request,
    operator: Operator = Depends(require_operator),
) -> None:
    """Revoke the current operations session."""

    token = request.headers.get("Authorization", "").partition(" ")[2]
    operations_repository = request.app.state.operations_repository
    operations_repository.create_audit_log(
        operator.__dict__, action="operations.logout", resource_type="session"
    )
    operations_repository.revoke_session(token)


@router.post("/admin/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    operator: Operator = Depends(require_operator),
) -> None:
    """Change the current operator's password and revoke their other sessions."""

    repository = request.app.state.operations_repository
    if not repository.change_password(
        operator.id,
        payload.current_password,
        payload.new_password,
        operator.session_id,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current password is incorrect")
    repository.create_audit_log(
        operator.__dict__, action="operations.password_changed", resource_type="operations_user", resource_id=operator.id
    )


@router.get("/admin/users", response_model=list[OperationsUserResponse])
def list_operations_users(
    request: Request,
    operator: Operator = Depends(require_admin),
) -> list[OperationsUserResponse]:
    """Return all operations users to administrators."""

    return [OperationsUserResponse(**row) for row in request.app.state.operations_repository.list_users()]


@router.post("/admin/users", response_model=OperationsUserResponse, status_code=status.HTTP_201_CREATED)
def create_operations_user(
    payload: OperationsUserCreateRequest,
    request: Request,
    operator: Operator = Depends(require_admin),
) -> OperationsUserResponse:
    """Create an operations account."""

    if payload.role not in {"admin", "support"}:
        raise HTTPException(status_code=400, detail="role must be admin or support")
    repository = request.app.state.operations_repository
    username = payload.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="username must contain at least 3 non-space characters")
    user = repository.create_user(username, payload.password, payload.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")
    repository.create_audit_log(
        operator.__dict__,
        action="operations.user_created",
        resource_type="operations_user",
        resource_id=user["id"],
        details={"username": user["username"], "role": user["role"]},
    )
    return OperationsUserResponse(**user)


@router.patch("/admin/users/{user_id}", response_model=OperationsUserResponse)
def update_operations_user(
    user_id: str,
    payload: OperationsUserUpdateRequest,
    request: Request,
    operator: Operator = Depends(require_admin),
) -> OperationsUserResponse:
    """Change an operations user's role or active state."""

    if payload.role not in {"admin", "support"}:
        raise HTTPException(status_code=400, detail="role must be admin or support")
    repository = request.app.state.operations_repository
    existing = repository.get_user(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="operations user not found")
    if user_id == operator.id and (payload.role != "admin" or not payload.is_active):
        raise HTTPException(status_code=400, detail="cannot remove your own administrator access")
    removes_admin = existing["role"] == "admin" and existing["is_active"] and (
        payload.role != "admin" or not payload.is_active
    )
    if removes_admin and repository.count_active_admins() <= 1:
        raise HTTPException(status_code=400, detail="at least one active administrator is required")
    user = repository.update_user(user_id, payload.role, payload.is_active)
    repository.create_audit_log(
        operator.__dict__,
        action="operations.user_updated",
        resource_type="operations_user",
        resource_id=user_id,
        details={"role": payload.role, "is_active": payload.is_active},
    )
    return OperationsUserResponse(**user)


@router.post("/admin/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_operations_password(
    user_id: str,
    payload: PasswordResetRequest,
    request: Request,
    operator: Operator = Depends(require_admin),
) -> None:
    """Reset a user's password and revoke all sessions for that account."""

    repository = request.app.state.operations_repository
    if user_id == operator.id:
        raise HTTPException(status_code=400, detail="use change-password for your own account")
    if not repository.reset_password(user_id, payload.new_password):
        raise HTTPException(status_code=404, detail="operations user not found")
    repository.create_audit_log(
        operator.__dict__, action="operations.password_reset", resource_type="operations_user", resource_id=user_id
    )


@router.get("/admin/sessions", response_model=list[OperationsSessionResponse])
def list_operations_sessions(
    request: Request,
    operator: Operator = Depends(require_operator),
) -> list[OperationsSessionResponse]:
    """List all sessions for admins, or only the current user's sessions for support."""

    user_id = None if operator.role == "admin" else operator.id
    sessions = request.app.state.operations_repository.list_sessions(user_id=user_id)
    return [OperationsSessionResponse(**row, is_current=row["id"] == operator.session_id) for row in sessions]


@router.delete("/admin/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_operations_session(
    session_id: str,
    request: Request,
    operator: Operator = Depends(require_operator),
) -> None:
    """Revoke an owned session, or any session when called by an administrator."""

    repository = request.app.state.operations_repository
    target = repository.get_session(session_id)
    if not target:
        raise HTTPException(status_code=404, detail="operations session not found")
    if operator.role != "admin" and target["user_id"] != operator.id:
        raise HTTPException(status_code=403, detail="cannot revoke another user's session")
    repository.revoke_session_by_id(session_id)
    repository.create_audit_log(
        operator.__dict__,
        action="operations.session_revoked",
        resource_type="operations_session",
        resource_id=session_id,
        details={"user_id": target["user_id"]},
    )


@router.get("/admin/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    request: Request,
    limit: int = 100,
    operator: Operator = Depends(require_admin),
) -> list[AuditLogResponse]:
    """Return recent operations audit entries to administrators."""

    safe_limit = min(max(limit, 1), 500)
    rows = request.app.state.operations_repository.list_audit_logs(safe_limit)
    return [AuditLogResponse(**row) for row in rows]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRecordResponse],
)
def list_conversation_messages(
    conversation_id: str,
    request: Request,
    operator: Operator = Depends(require_operator),
) -> list[MessageRecordResponse]:
    """Return persisted message history for one conversation."""

    conversation_repository = request.app.state.conversation_repository
    return [MessageRecordResponse(**row) for row in conversation_repository.list_messages(conversation_id)]


@router.get(
    "/handoff-tickets",
    response_model=list[HandoffTicketRecordResponse],
)
def list_handoff_tickets(
    request: Request,
    status: Optional[str] = "open",
    operator: Operator = Depends(require_operator),
) -> list[HandoffTicketRecordResponse]:
    """Return human handoff tickets for operations or human support queues."""

    conversation_repository = request.app.state.conversation_repository
    return [HandoffTicketRecordResponse(**row) for row in conversation_repository.list_handoff_tickets(status=status)]


@router.patch(
    "/handoff-tickets/{ticket_id}",
    response_model=HandoffTicketRecordResponse,
)
def update_handoff_ticket(
    ticket_id: str,
    payload: HandoffTicketUpdateRequest,
    request: Request,
    operator: Operator = Depends(require_operator),
) -> HandoffTicketRecordResponse:
    """Update a human handoff ticket status and handling details."""

    if payload.status not in {"open", "in_progress", "resolved"}:
        raise HTTPException(status_code=400, detail="status must be open, in_progress or resolved")

    conversation_repository = request.app.state.conversation_repository
    ticket = conversation_repository.update_handoff_ticket(
        ticket_id=ticket_id,
        status=payload.status,
        assigned_to=operator.username,
        resolution_note=payload.resolution_note,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="handoff ticket not found")
    request.app.state.operations_repository.create_audit_log(
        operator.__dict__,
        action="handoff.update",
        resource_type="handoff_ticket",
        resource_id=ticket_id,
        details={"status": payload.status, "resolution_note": payload.resolution_note},
    )
    return HandoffTicketRecordResponse(**ticket)
