"""Channel adapter service for external sales and support message sources."""

from app.models.schemas import ChannelMessageRequest, ChannelMessageResponse, ChatRequest
from app.services.conversation_repository import ConversationRepository
from app.services.conversation_service import ConversationService


class ChannelAdapterService:
    """Normalize channel-specific inbound messages into internal chat turns."""

    def __init__(self, conversation_service: ConversationService, repository: ConversationRepository) -> None:
        self.conversation_service = conversation_service
        self.repository = repository

    def handle_message(self, channel: str, payload: ChannelMessageRequest) -> ChannelMessageResponse:
        """Handle one inbound message from a named channel."""

        conversation_id = self.repository.get_channel_conversation(channel, payload.external_conversation_id)
        response = self.conversation_service.handle_chat(
            ChatRequest(
                message=payload.message,
                user_id=payload.external_user_id,
                conversation_id=conversation_id,
                channel=channel,
            )
        )
        self.repository.upsert_channel_conversation(
            channel=channel,
            external_conversation_id=payload.external_conversation_id,
            conversation_id=response.conversation_id or "",
        )
        return ChannelMessageResponse(
            channel=channel,
            external_conversation_id=payload.external_conversation_id,
            conversation_id=response.conversation_id or "",
            answer=response.answer,
            needs_handoff=response.needs_handoff,
            handoff=response.handoff,
        )
