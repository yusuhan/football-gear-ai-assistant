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
        settings = Settings(database_url="")
        initialize_database(settings)
        repository = ProductRepository(settings.database_target())
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

    def test_narrow_foot_question_filters_by_boot_fit(self) -> None:
        response = self.agent.answer(ChatRequest(message="我脚比较窄适合哪些足球鞋"))

        self.assertEqual(response.intent, "product_recommendation")
        self.assertEqual(response.tool_calls[0].arguments["fit_profile"], "narrow")
        self.assertIn("Mercurial", response.answer)
        self.assertNotIn("Tiempo", response.answer)

    def test_apparel_size_question_requests_missing_measurements(self) -> None:
        response = self.agent.answer(ChatRequest(message="我180cm球衣穿什么码"))

        self.assertEqual(response.intent, "apparel_size_clarification")
        self.assertEqual(response.route, "clarification")
        self.assertIn("体重和胸围", response.answer)
        self.assertNotIn("FG", response.answer)

    def test_shin_guard_question_returns_shin_guards(self) -> None:
        response = self.agent.answer(ChatRequest(message="护腿板有什么推荐的吗"))

        self.assertEqual(response.intent, "product_recommendation")
        self.assertEqual(response.tool_calls[0].arguments["category"], "shin_guards")
        self.assertIn("Shin Guards", response.answer)
        self.assertNotIn("Tiempo", response.answer)

    def test_socks_and_jersey_questions_use_their_categories(self) -> None:
        socks = self.agent.answer(ChatRequest(message="推荐一双足球袜"))
        jersey = self.agent.answer(ChatRequest(message="推荐训练球衣"))

        self.assertEqual(socks.tool_calls[0].arguments["category"], "football_socks")
        self.assertIn("Socks", socks.answer)
        self.assertEqual(jersey.tool_calls[0].arguments["category"], "football_apparel")
        self.assertIn("Jersey", jersey.answer)


if __name__ == "__main__":
    unittest.main()
