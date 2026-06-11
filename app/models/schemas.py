"""Pydantic schemas shared by API, Agent and tool layers."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request sent by a customer."""

    message: str = Field(..., min_length=1, description="Customer message")
    user_id: Optional[str] = Field(default="demo_user", description="Optional user identifier")
    conversation_id: Optional[str] = Field(default=None, description="Conversation id for multi-turn support")
    session_id: Optional[str] = Field(default=None, description="Deprecated alias for conversation_id")
    channel: str = Field(default="web", description="Message channel such as web, taobao, 1688 or wecom")


class ChannelMessageRequest(BaseModel):
    """Inbound message payload from an external sales or support channel."""

    external_user_id: str = Field(..., min_length=1, description="User id from the external channel")
    external_conversation_id: str = Field(..., min_length=1, description="Conversation/thread id from the channel")
    message: str = Field(..., min_length=1, description="Customer text message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Raw channel-specific metadata")


class SourceSnippet(BaseModel):
    """Knowledge source used to support an FAQ answer."""

    article_id: str
    question: str
    score: float


class ToolCallRecord(BaseModel):
    """Tool call trace returned for interview/debug visibility."""

    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class HandoffTicketResponse(BaseModel):
    """Human handoff ticket attached to an AI response."""

    ticket_id: str
    reason: str
    status: str


class ChannelMessageResponse(BaseModel):
    """Response returned to a channel adapter."""

    channel: str
    external_conversation_id: str
    conversation_id: str
    answer: str
    needs_handoff: bool
    handoff: Optional[HandoffTicketResponse] = None


class ChatResponse(BaseModel):
    """Answer returned by the support agent."""

    conversation_id: Optional[str] = None
    answer: str
    intent: str
    confidence: float
    route: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    sources: List[SourceSnippet] = Field(default_factory=list)
    needs_handoff: bool = False
    handoff: Optional[HandoffTicketResponse] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    products: int
    inventory_rows: int
    faq_articles: int
    conversations: int
    open_handoffs: int


class AdminLoginRequest(BaseModel):
    """Credentials submitted by an operations user."""

    username: str = Field(..., min_length=1, description="Operations username")
    password: str = Field(..., min_length=1, description="Operations password")


class OperatorResponse(BaseModel):
    """Authenticated operations user."""

    id: str
    username: str
    role: str


class AdminLoginResponse(BaseModel):
    """Successful operations session response."""

    access_token: str
    token_type: str = "bearer"
    expires_at: str
    operator: OperatorResponse


class AuditLogResponse(BaseModel):
    """One sensitive operations action recorded for review."""

    id: str
    actor_username: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: dict[str, Any]
    created_at: str


class PasswordChangeRequest(BaseModel):
    """Password update requested by the current operator."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class OperationsUserCreateRequest(BaseModel):
    """Administrator request for a new operations account."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: str = Field(default="support")


class OperationsUserUpdateRequest(BaseModel):
    """Administrator request to change role or active state."""

    role: str
    is_active: bool


class PasswordResetRequest(BaseModel):
    """Administrator password reset request."""

    new_password: str = Field(..., min_length=8)


class OperationsUserResponse(BaseModel):
    """Operations user safe for administrative display."""

    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class OperationsSessionResponse(BaseModel):
    """One active operations session."""

    id: str
    user_id: str
    username: str
    role: str
    expires_at: str
    created_at: str
    is_current: bool = False


class ProductResponse(BaseModel):
    """Product record exposed by GET /products."""

    id: str
    name: str
    brand: str
    category: str
    price: int
    surface: str
    description: str
    recommended_position: str


class InventoryResponse(BaseModel):
    """Inventory record exposed by GET /inventory."""

    product_id: str
    product_name: str
    size: int
    stock: int


class MessageRecordResponse(BaseModel):
    """Persisted conversation message returned by history APIs."""

    id: str
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = None
    route: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str


class HandoffTicketRecordResponse(BaseModel):
    """Persisted human handoff ticket."""

    id: str
    conversation_id: str
    reason: str
    status: str
    assigned_to: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str
    updated_at: str


class HandoffTicketUpdateRequest(BaseModel):
    """Request used by human agents to update a handoff ticket."""

    status: str = Field(..., description="Ticket status: open, in_progress or resolved")
    assigned_to: Optional[str] = Field(default=None, description="Human agent handling the ticket")
    resolution_note: Optional[str] = Field(default=None, description="Resolution notes when closing a ticket")
