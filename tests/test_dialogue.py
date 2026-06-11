"""Tests for the football gear customer service Agent."""

import unittest

from app.models.schemas import ChatRequest
from app.core.config import Settings
from app.db.database import initialize_database
from app.services.agent import FootballGearAgent
from app.services.product_repository import ProductRepository
from app.services.rag import FAQKnowledgeBase
from app.services.tools import ToolRouter


class FootballGearAgentTest(unittest.TestCase):
    """Validate tool routing and FAQ fallback."""

    def setUp(self) -> None:
        settings = Settings()
        initialize_database(settings)
        repository = ProductRepository(settings.database_path)
        self.agent = FootballGearAgent(
            tool_router=ToolRouter(repository),
            faq_knowledge_base=FAQKnowledgeBase.from_json(settings.faq_path),
        )

    def test_inventory_question_calls_inventory_tool(self) -> None:
        response = self.agent.answer(ChatRequest(message="Mercurial 16 Elite有43码吗"))

        self.assertEqual(response.intent, "inventory_check")
        self.assertEqual(response.route, "tool")
        self.assertEqual(response.tool_calls[0].name, "check_inventory")
        self.assertIn("12", response.answer)

    def test_size_question_calls_size_tool(self) -> None:
        response = self.agent.answer(ChatRequest(message="脚长27厘米穿什么码"))

        self.assertEqual(response.intent, "size_recommendation")
        self.assertEqual(response.tool_calls[0].name, "get_size_recommendation")
        self.assertIn("43", response.answer)

    def test_shipping_question_uses_rag(self) -> None:
        response = self.agent.answer(ChatRequest(message="多久发货"))

        self.assertEqual(response.intent, "faq")
        self.assertEqual(response.route, "rag")
        self.assertEqual(response.sources[0].article_id, "FAQ001")


if __name__ == "__main__":
    unittest.main()
