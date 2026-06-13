"""Rules for deciding when AI should hand a conversation to a human."""

from dataclasses import dataclass

from app.models.schemas import ChatRequest, ChatResponse

ESCALATION_KEYWORDS = [
    "投诉",
    "退款",
    "赔偿",
    "差评",
    "生气",
    "假货",
    "质量问题",
    "退钱",
]

HUMAN_REQUEST_PHRASES = [
    "转人工",
    "人工客服",
    "找客服",
    "联系人工",
    "真人客服",
    "客服介入",
    "我要人工",
]

ORDER_EXCEPTION_KEYWORDS = [
    "物流没动",
    "物流不动",
    "一直没发货",
    "订单异常",
    "快递丢了",
    "少发",
    "漏发",
]


@dataclass(frozen=True)
class HandoffDecision:
    """Decision returned by handoff policy evaluation."""

    should_handoff: bool
    reason: str


class HandoffPolicy:
    """Small rule engine for human handoff decisions."""

    def __init__(self, low_confidence_threshold: float = 0.45) -> None:
        self.low_confidence_threshold = low_confidence_threshold

    def evaluate(self, request: ChatRequest, response: ChatResponse) -> HandoffDecision:
        """Decide whether a user turn needs human support."""

        matched_keyword = next(
            (
                keyword
                for keyword in ESCALATION_KEYWORDS + HUMAN_REQUEST_PHRASES + ORDER_EXCEPTION_KEYWORDS
                if keyword in request.message
            ),
            None,
        )
        if matched_keyword:
            return HandoffDecision(True, f"escalation_keyword:{matched_keyword}")

        self_service_routes = {"fallback", "clarification", "self_service"}
        if response.route not in self_service_routes and response.confidence < self.low_confidence_threshold:
            return HandoffDecision(True, f"low_confidence:{response.confidence}")

        return HandoffDecision(False, "")
