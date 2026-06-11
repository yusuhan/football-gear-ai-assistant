"""Rules for deciding when AI should hand a conversation to a human."""

from dataclasses import dataclass

from app.models.schemas import ChatRequest, ChatResponse

SENSITIVE_KEYWORDS = [
    "人工",
    "客服",
    "投诉",
    "退款",
    "赔偿",
    "差评",
    "生气",
    "假货",
    "质量问题",
    "退钱",
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

        matched_keyword = next((keyword for keyword in SENSITIVE_KEYWORDS if keyword in request.message), None)
        if matched_keyword:
            return HandoffDecision(True, f"sensitive_keyword:{matched_keyword}")

        if response.route == "fallback":
            return HandoffDecision(True, "fallback_no_answer")

        if response.confidence < self.low_confidence_threshold:
            return HandoffDecision(True, f"low_confidence:{response.confidence}")

        return HandoffDecision(False, "")
