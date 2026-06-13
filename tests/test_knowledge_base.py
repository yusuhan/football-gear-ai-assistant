"""Tests for FAQ RAG retrieval."""

import unittest
from pathlib import Path

from app.services.rag import FAQKnowledgeBase


class FAQKnowledgeBaseTest(unittest.TestCase):
    """Validate deterministic FAQ search behavior."""

    def test_shipping_question_matches_shipping_faq(self) -> None:
        knowledge_base = FAQKnowledgeBase.from_json(Path("data/faq.json"))

        hits = knowledge_base.search("多久发货")

        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].article.article_id, "FAQ001")

    def test_unrelated_apparel_size_does_not_match_boot_surface(self) -> None:
        knowledge_base = FAQKnowledgeBase.from_json(Path("data/faq.json"))

        hits = knowledge_base.search("我180cm球衣穿什么码")

        self.assertNotIn("FAQ012", [hit.article.article_id for hit in hits])


if __name__ == "__main__":
    unittest.main()
