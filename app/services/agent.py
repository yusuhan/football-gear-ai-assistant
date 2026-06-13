"""Football gear Agent orchestration.

The Agent demonstrates the key interview concepts: intent routing, tool calling
and RAG. OpenAI function calling can be enabled with USE_OPENAI=true, while the
deterministic router keeps the MVP runnable without external quota.
"""

import json
import os
import re
from typing import Any, Callable, Optional

from app.models.schemas import ChatRequest, ChatResponse, SourceSnippet, ToolCallRecord
from app.services.rag import FAQHit, FAQKnowledgeBase
from app.services.tools import OPENAI_TOOL_DEFINITIONS, ToolRouter

FALLBACK_ANSWER = "我还没有找到足够准确的信息。你可以告诉我位置、预算、尺码、脚长或具体商品名，我会继续帮你查。"
IDENTITY_ANSWER = (
    "我是商家工作流中的足球装备智能客服，负责接待商品咨询、装备推荐、库存尺码和售后政策问题。"
    "我会调用商家的商品、库存和知识库来回答；涉及具体订单异常、投诉退款或你明确要求真人时，"
    "我会创建工单交给人工客服继续处理。"
)
APPAREL_SIZE_CLARIFICATION = (
    "仅凭身高还不能准确推荐球衣尺码。请再提供体重和胸围，并告诉我具体品牌或款式；"
    "不同品牌版型差异较大，当前没有对应尺码表时我不会直接猜尺码。"
)

PRODUCT_ALIASES = {
    "Mercurial": ["mercurial", "刺客"],
    "Predator": ["predator", "猎鹰"],
    "Tiempo": ["tiempo", "传奇"],
    "Goalkeeper Gloves": ["手套"],
}

POSITION_ALIASES = {
    "Winger": ["边锋", "速度", "突破"],
    "Goalkeeper": ["守门员", "门将"],
    "Midfielder": ["中场", "传控"],
    "Defender": ["后卫", "防守"],
}

CATEGORY_ALIASES = [
    ("football_boots", ["足球鞋", "球鞋", "战靴"]),
    ("shin_guards", ["护腿板", "插板", "护板"]),
    ("football_apparel", ["球衣", "足球服", "训练服", "比赛服"]),
    ("football_socks", ["球袜", "足球袜", "袜子", "防滑袜"]),
    ("footballs", ["足球", "比赛球", "训练球"]),
    ("goalkeeper_gloves", ["守门员手套", "门将手套", "手套"]),
    ("protective_gear", ["护具", "护膝", "护肘"]),
]


class FootballGearAgent:
    """Agent that routes customer messages to tools or FAQ retrieval."""

    def __init__(
        self,
        tool_router: ToolRouter,
        faq_knowledge_base: FAQKnowledgeBase,
        use_openai: bool = False,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self.tool_router = tool_router
        self.faq_knowledge_base = faq_knowledge_base
        self.use_openai = use_openai and bool(os.getenv("OPENAI_API_KEY"))
        self.model = model

    def answer(self, request: ChatRequest) -> ChatResponse:
        """Answer a customer message through OpenAI tools or local routing."""

        if self.is_identity_question(request.message):
            return self._identity_response()

        if self.use_openai:
            try:
                return self._answer_with_openai(request.message)
            except Exception:
                # Local fallback is deliberate: demos should not fail because of
                # quota, model access or transient network issues.
                return self._answer_with_local_router(request.message)
        return self._answer_with_local_router(request.message)

    def _answer_with_local_router(self, message: str) -> ChatResponse:
        """Deterministic routing used for local demos and tests."""

        if self._is_apparel_size_question(message):
            return ChatResponse(
                answer=APPAREL_SIZE_CLARIFICATION,
                intent="apparel_size_clarification",
                confidence=0.92,
                route="clarification",
            )

        local_routes: list[tuple[str, Callable[[str], Optional[dict[str, Any]]]]] = [
            ("check_inventory", self._extract_inventory_args),
            ("get_size_recommendation", self._extract_size_args),
            ("search_products", self._extract_recommendation_args),
        ]

        for tool_name, extract_args in local_routes:
            arguments = extract_args(message)
            if arguments:
                result = self.tool_router.execute(tool_name, arguments)
                return self._format_tool_response(tool_name, arguments, result)

        faq_hits = self.faq_knowledge_base.search(message)
        if faq_hits:
            return self._faq_response(faq_hits)

        return ChatResponse(answer=FALLBACK_ANSWER, intent="fallback", confidence=0.2, route="fallback")

    def can_answer_during_handoff(self, message: str) -> bool:
        """Allow harmless assistant identity questions while a human ticket is active."""

        return self.is_identity_question(message)

    @staticmethod
    def _identity_response() -> ChatResponse:
        """Describe the assistant's role without invoking tools or a model."""

        return ChatResponse(
            answer=IDENTITY_ANSWER,
            intent="assistant_identity",
            confidence=0.98,
            route="self_service",
        )

    @staticmethod
    def is_identity_question(message: str) -> bool:
        """Detect questions about the assistant and its role in the merchant workflow."""

        normalized = re.sub(r"[？?。！!\s]", "", message.lower())
        exact_phrases = {
            "你是谁",
            "你是什么",
            "你是什么东西",
            "你是机器人吗",
            "你是ai吗",
            "你是客服吗",
            "你能做什么",
            "你的功能",
            "你的能力",
        }
        return normalized in exact_phrases or normalized.endswith("你是谁")

    def _answer_with_openai(self, message: str) -> ChatResponse:
        """Use OpenAI function calling when an API key is available."""

        from openai import OpenAI

        client = OpenAI()
        first = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a football gear retail support agent. "
                        "Use tools for inventory, product recommendations and size advice. "
                        "For shipping, return and policy questions, answer from FAQ retrieval context."
                    ),
                },
                {"role": "user", "content": message},
            ],
            tools=OPENAI_TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        assistant_message = first.choices[0].message
        if assistant_message.tool_calls:
            tool_call = assistant_message.tool_calls[0]
            arguments = json.loads(tool_call.function.arguments or "{}")
            result = self.tool_router.execute(tool_call.function.name, arguments)
            return self._format_tool_response(tool_call.function.name, arguments, result)

        faq_hits = self.faq_knowledge_base.search(message)
        if faq_hits:
            return self._faq_response(faq_hits)
        return ChatResponse(
            answer=assistant_message.content or "我还需要更多信息才能回答。",
            intent="openai_direct",
            confidence=0.7,
            route="llm",
        )

    def _format_tool_response(self, tool_name: str, arguments: dict[str, Any], result: dict[str, Any]) -> ChatResponse:
        """Format tool output from either local routing or OpenAI routing."""

        if tool_name == "check_inventory":
            return self._inventory_response(arguments, result)
        if tool_name == "get_size_recommendation":
            return self._size_response(arguments, result)
        if tool_name == "search_products":
            return self._recommendation_response(arguments, result)
        return ChatResponse(answer="工具已执行，但暂时无法格式化结果。", intent="tool_call", confidence=0.5, route="tool")

    def _inventory_response(self, arguments: dict[str, Any], result: dict[str, Any]) -> ChatResponse:
        """Format inventory tool output."""

        tool_call = ToolCallRecord(name="check_inventory", arguments=arguments, result=result)
        if result.get("available"):
            answer = f"{result['product_name']} {result['size']}码有货，当前库存 {result['stock']} 双。"
            confidence = 0.92
        else:
            answer = f"暂时没有查到 {arguments['product_name']} {arguments['size']}码库存，建议换尺码或联系人工确认。"
            confidence = 0.72
        return ChatResponse(
            answer=answer,
            intent="inventory_check",
            confidence=confidence,
            route="tool",
            tool_calls=[tool_call],
        )

    def _size_response(self, arguments: dict[str, Any], result: dict[str, Any]) -> ChatResponse:
        """Format size guide tool output."""

        tool_call = ToolCallRecord(name="get_size_recommendation", arguments=arguments, result=result)
        size = result.get("recommended_size")
        if size:
            answer = f"脚长 {arguments['foot_length']}cm 建议先试 {size} 码。如果脚背高或脚宽，建议大半码或选择鞋楦更宽的款式。"
            confidence = 0.88
        else:
            answer = "我没有找到对应脚长的尺码表，请补充脚长厘米数或联系人工。"
            confidence = 0.5
        return ChatResponse(
            answer=answer,
            intent="size_recommendation",
            confidence=confidence,
            route="tool",
            tool_calls=[tool_call],
        )

    def _recommendation_response(self, arguments: dict[str, Any], result: dict[str, Any]) -> ChatResponse:
        """Format product search tool output."""

        tool_call = ToolCallRecord(name="search_products", arguments=arguments, result=result)
        products = result.get("products", [])
        if not products:
            return ChatResponse(
                answer="当前没有找到完全符合位置和预算的商品，可以放宽预算或告诉我偏好的品牌。",
                intent="product_recommendation",
                confidence=0.65,
                route="tool",
                tool_calls=[tool_call],
            )

        lines = ["根据你的需求，推荐："]
        for product in products[:3]:
            details = product["description"].rstrip("。")
            if product["category"] == "football_boots":
                fit_text = {"narrow": "偏窄鞋楦", "regular": "常规鞋楦", "wide": "偏宽鞋楦"}.get(
                    product.get("fit_profile"),
                    "常规鞋楦",
                )
                details = f"{fit_text}，{details}"
            lines.append(f"- {product['name']}：{details}，价格 {product['price']} 元。")
        if arguments.get("fit_profile"):
            lines.append("鞋楦标注来自当前商品资料，实际包裹感还会受脚背高度和袜子厚度影响。")
        return ChatResponse(
            answer="\n".join(lines),
            intent="product_recommendation",
            confidence=0.86,
            route="tool",
            tool_calls=[tool_call],
        )

    def _faq_response(self, hits: list[FAQHit]) -> ChatResponse:
        """Format FAQ retrieval output."""

        best_hit = hits[0]
        return ChatResponse(
            answer=best_hit.article.answer,
            intent="faq",
            confidence=min(best_hit.score, 0.95),
            route="rag",
            sources=[
                SourceSnippet(article_id=hit.article.article_id, question=hit.article.question, score=hit.score)
                for hit in hits
            ],
        )

    def _extract_inventory_args(self, message: str) -> Optional[dict[str, Any]]:
        """Extract product name and size for inventory checks."""

        if not any(keyword in message for keyword in ["有货", "库存", "有码", "还有", "码吗"]):
            return None
        size_match = re.search(r"(\d{2})\s*码", message)
        size = int(size_match.group(1)) if size_match else None
        if size:
            return {"product_name": self._guess_product_name(message), "size": size}
        return None

    def _extract_size_args(self, message: str) -> Optional[dict[str, Any]]:
        """Extract foot length for size recommendations."""

        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:cm|厘米)", message.lower())
        if match and any(keyword in message for keyword in ["脚长", "穿什么码", "尺码", "多大码"]):
            return {"foot_length": float(match.group(1))}
        return None

    def _extract_recommendation_args(self, message: str) -> Optional[dict[str, Any]]:
        """Extract position and budget for product recommendations."""

        if not any(keyword in message for keyword in ["推荐", "买什么", "适合"]):
            return None
        budget_match = re.search(r"(\d{3,5})\s*元?(?:以内|以下|预算)?", message)
        budget = int(budget_match.group(1)) if budget_match else None
        position = self._guess_position(message)
        fit_profile = self._guess_fit_profile(message)
        category = self._guess_category(message)
        return {
            "position": position,
            "budget": budget,
            "fit_profile": fit_profile,
            "category": category,
        }

    def _is_apparel_size_question(self, message: str) -> bool:
        """Detect apparel sizing so shoe and surface advice cannot answer it."""

        apparel_keywords = ["球衣", "上衣", "短袖", "长袖", "裤子", "服装"]
        size_keywords = ["什么码", "多大码", "尺码", "穿几码", "穿什么"]
        return any(keyword in message for keyword in apparel_keywords) and any(
            keyword in message for keyword in size_keywords
        )

    def _guess_fit_profile(self, message: str) -> Optional[str]:
        """Map user foot shape to the catalog fit profile."""

        if any(keyword in message for keyword in ["脚窄", "窄脚", "比较窄", "瘦脚"]):
            return "narrow"
        if any(keyword in message for keyword in ["脚宽", "宽脚", "比较宽", "大宽脚"]):
            return "wide"
        return None

    def _guess_category(self, message: str) -> Optional[str]:
        """Map customer language to a catalog category."""

        for category, aliases in CATEGORY_ALIASES:
            if any(alias in message for alias in aliases):
                return category
        return None

    def _guess_product_name(self, message: str) -> str:
        """Map partial user text to a demo product name."""

        normalized = message.lower()
        for product_name, aliases in PRODUCT_ALIASES.items():
            if any(alias in normalized or alias in message for alias in aliases):
                return product_name
        return "Mercurial"

    def _guess_position(self, message: str) -> Optional[str]:
        """Map Chinese football roles to product tags."""

        for position, aliases in POSITION_ALIASES.items():
            if any(alias in message for alias in aliases):
                return position
        return None
