"""FastAPI application entry point for Football Gear AI Assistant."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_SUPPORT_PASSWORD, Settings
from app.db.database import initialize_database
from app.services.agent import FootballGearAgent
from app.services.channel_adapter import ChannelAdapterService
from app.services.conversation_repository import ConversationRepository
from app.services.conversation_service import ConversationService
from app.services.product_repository import ProductRepository
from app.services.operations_repository import OperationsRepository
from app.services.rag import FAQKnowledgeBase
from app.services.tools import ToolRouter


def create_app() -> FastAPI:
    """Create the API app and wire all local dependencies."""

    settings = Settings()
    if settings.app_env != "local" and (
        settings.admin_password == DEFAULT_ADMIN_PASSWORD or settings.support_password == DEFAULT_SUPPORT_PASSWORD
    ):
        raise RuntimeError("Operations passwords must be changed outside the local environment")
    initialize_database(settings)
    database_target = settings.database_target()
    repository = ProductRepository(database_target)
    conversation_repository = ConversationRepository(database_target)
    operations_repository = OperationsRepository(database_target, settings.operations_session_hours)
    faq_knowledge_base = FAQKnowledgeBase.from_json(settings.faq_path, min_score=settings.min_rag_score)
    tool_router = ToolRouter(repository=repository)
    agent = FootballGearAgent(
        tool_router=tool_router,
        faq_knowledge_base=faq_knowledge_base,
        use_openai=settings.use_openai,
        model=settings.openai_model,
    )
    conversation_service = ConversationService(agent=agent, repository=conversation_repository)
    channel_adapter_service = ChannelAdapterService(
        conversation_service=conversation_service,
        repository=conversation_repository,
    )

    app = FastAPI(
        title="Football Gear AI Assistant",
        description="足球用品零售智能客服 MVP：Agent + Tool Calling + RAG + FastAPI",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Conversation-Id"],
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.conversation_repository = conversation_repository
    app.state.operations_repository = operations_repository
    app.state.conversation_service = conversation_service
    app.state.channel_adapter_service = channel_adapter_service
    app.state.faq_knowledge_base = faq_knowledge_base
    app.state.agent = agent
    app.include_router(router)
    return app


app = create_app()
