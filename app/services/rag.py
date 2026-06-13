"""FAQ retrieval for RAG-style answers.

The MVP uses an in-memory lexical index. The class boundary mirrors what a
ChromaDB-backed retriever would expose, so the retrieval engine can be swapped
without changing the Agent or API layer.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

CHINESE_STOP_BIGRAMS = {
    "什么",
    "怎么",
    "如何",
    "哪些",
    "多少",
    "可以",
    "是否",
    "问题",
}


@dataclass(frozen=True)
class FAQArticle:
    """One FAQ knowledge item."""

    article_id: str
    question: str
    answer: str
    tags: list[str]


@dataclass(frozen=True)
class FAQHit:
    """FAQ retrieval result."""

    article: FAQArticle
    score: float


class FAQKnowledgeBase:
    """Searchable FAQ knowledge base."""

    def __init__(self, articles: list[FAQArticle], min_score: float = 0.12) -> None:
        self.articles = articles
        self.min_score = min_score
        self._indexed_articles = [(article, self._tokenize(self._article_text(article))) for article in articles]

    @property
    def article_count(self) -> int:
        """Return loaded FAQ article count."""

        return len(self.articles)

    @classmethod
    def from_json(cls, path: Path, min_score: float = 0.12) -> "FAQKnowledgeBase":
        """Load FAQ articles from JSON."""

        with path.open("r", encoding="utf-8") as file:
            raw_articles = json.load(file)

        return cls(
            articles=[
                FAQArticle(
                    article_id=item["article_id"],
                    question=item["question"],
                    answer=item["answer"],
                    tags=item.get("tags", []),
                )
                for item in raw_articles
            ],
            min_score=min_score,
        )

    def search(self, query: str, limit: int = 3) -> list[FAQHit]:
        """Retrieve FAQ articles by mixed Chinese/English token overlap."""

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[FAQHit] = []
        for article, article_tokens in self._indexed_articles:
            overlap = query_tokens.intersection(article_tokens)
            if not overlap:
                continue
            score = round(len(overlap) / max(len(query_tokens), 1), 3)
            if score >= self.min_score:
                hits.append(FAQHit(article=article, score=score))

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    def _article_text(self, article: FAQArticle) -> str:
        """Concatenate fields used for retrieval."""

        return " ".join([article.question, article.answer, " ".join(article.tags)])

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize a mixed Chinese/English query into simple lexical features."""

        lowered = text.lower()
        english_tokens = re.findall(r"[a-z0-9_]+", lowered)
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
        chinese_bigrams = [
            left + right
            for left, right in zip(chinese_chars, chinese_chars[1:])
            if left + right not in CHINESE_STOP_BIGRAMS
        ]
        # Single Chinese characters create false positives such as matching
        # "球衣尺码" to a football-boot surface article solely through "球".
        return set(english_tokens + chinese_bigrams)
