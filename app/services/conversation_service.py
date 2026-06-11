"""Application service that wraps Agent answers with durable conversation state."""

from typing import Optional

from app.models.schemas import ChatRequest, ChatResponse, HandoffTicketResponse
from app.services.agent import FootballGearAgent
from app.services.conversation_repository import ConversationRepository
from app.services.handoff_policy import HandoffPolicy

HANDOFF_WAITING_ANSWER = "这次会话已经转接人工客服，我已记录你的补充消息，请等待人工继续处理。"


class ConversationService:
    """Coordinate conversation persistence around the stateless Agent."""

    def __init__(
        self,
        agent: FootballGearAgent,
        repository: ConversationRepository,
        handoff_policy: Optional[HandoffPolicy] = None,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.handoff_policy = handoff_policy or HandoffPolicy()

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Persist a user turn, ask the Agent, then persist the assistant turn."""

        conversation_id = self.repository.get_or_create_conversation(
            conversation_id=request.conversation_id or request.session_id,
            user_id=request.user_id or "anonymous",
            channel=request.channel,
        )
        self.repository.create_message(conversation_id, role="user", content=request.message)

        active_handoff = self.repository.get_active_handoff_ticket(conversation_id)
        if active_handoff:
            return self._handoff_waiting_response(conversation_id, active_handoff)

        response = self.agent.answer(request)
        response.conversation_id = conversation_id

        assistant_message_id = self.repository.create_message(
            conversation_id,
            role="assistant",
            content=response.answer,
            intent=response.intent,
            route=response.route,
            confidence=response.confidence,
        )
        for tool_call in response.tool_calls:
            self.repository.create_tool_call_log(
                conversation_id,
                assistant_message_id,
                tool_call.name,
                tool_call.arguments,
                tool_call.result,
            )

        handoff_decision = self.handoff_policy.evaluate(request, response)
        if handoff_decision.should_handoff:
            ticket = self.repository.create_handoff_ticket(conversation_id, handoff_decision.reason)
            response.needs_handoff = True
            response.handoff = HandoffTicketResponse(
                ticket_id=ticket["id"],
                reason=ticket["reason"],
                status=ticket["status"],
            )

        self.repository.create_agent_event(
            conversation_id,
            "agent_response",
            {
                "intent": response.intent,
                "route": response.route,
                "confidence": response.confidence,
                "sources": [source.model_dump() for source in response.sources],
                "needs_handoff": response.needs_handoff,
                "handoff_reason": response.handoff.reason if response.handoff else None,
            },
            message_id=assistant_message_id,
        )
        return response

    def _handoff_waiting_response(self, conversation_id: str, ticket: dict) -> ChatResponse:
        """Return a waiting response without invoking the AI Agent."""

        response = ChatResponse(
            conversation_id=conversation_id,
            answer=HANDOFF_WAITING_ANSWER,
            intent="human_handoff",
            confidence=1.0,
            route="handoff",
            needs_handoff=True,
            handoff=HandoffTicketResponse(
                ticket_id=ticket["id"],
                reason=ticket["reason"],
                status=ticket["status"],
            ),
        )
        assistant_message_id = self.repository.create_message(
            conversation_id,
            role="assistant",
            content=response.answer,
            intent=response.intent,
            route=response.route,
            confidence=response.confidence,
        )
        self.repository.create_agent_event(
            conversation_id,
            "handoff_waiting",
            {
                "ticket_id": ticket["id"],
                "ticket_status": ticket["status"],
                "reason": ticket["reason"],
            },
            message_id=assistant_message_id,
        )
        return response
