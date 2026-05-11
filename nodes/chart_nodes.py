import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_vision_llm: ChatOpenAI | None = None
_feedback_llm: ChatOpenAI | None = None


def _get_vision_llm() -> ChatOpenAI:
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return _vision_llm


def _get_feedback_llm() -> ChatOpenAI:
    global _feedback_llm
    if _feedback_llm is None:
        _feedback_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _feedback_llm


_ICT_SYSTEM = """\
You are an expert ICT (Inner Circle Trader) technical analyst. Analyze the trading chart image.

Evaluate the following ICT concepts:
1. Market Structure: trend direction, BOS (Break of Structure), CHoCH (Change of Character)
2. Liquidity: BSL/SSL sweeps, equal highs/lows, stop hunts before the move
3. PD Arrays: FVG (Fair Value Gap), Order Block (OB), Breaker Block, Mitigation Block
4. Entry Model: OTE (62-79% Fibonacci retracement), AMD (Accumulation/Manipulation/Distribution)
5. Premium/Discount zones: Is the entry placed in discount (for buy) or premium (for sell)?

For each identifiable trade entry or setup visible on the chart:
- State which ICT concepts are present or absent
- Identify execution errors (e.g., entered in premium zone, missed the FVG, wrong OB selected)
- Note liquidity grabs or stop hunts that occurred before the move
- Assess whether the entry aligns with the higher timeframe bias

Be specific and concise. Respond entirely in Korean."""

_FEEDBACK_SYSTEM = """\
You are a trading coach. Given an ICT chart analysis text, extract structured feedback.
Return JSON with exactly these keys:
  ict_concepts:     list[str]  (ICT concepts identified, e.g. ["FVG", "OrderBlock", "BOS", "CHoCH"])
  entry_errors:     list[str]  (specific execution mistakes found in Korean)
  chart_weaknesses: list[str]  (short weakness tags in Korean, e.g. ["프리미엄진입", "유동성미확인", "OB미사용"])
  improvement:      str        (single most important improvement action in Korean)"""


def chart_analysis_node(state: dict) -> dict:
    """base64 차트 이미지 → OpenAI Vision(gpt-4o) → ICT 근거 분석."""
    session_id = state.get("session_id", "default")
    logger.info("chart_analysis_node start | session_id=%s", session_id)
    chart_image = state.get("chart_image", "").strip()
    if not chart_image:
        logger.info("chart_analysis_node: no chart_image, skipping")
        return {"chart_feedback": ""}

    # data URI prefix 제거
    if "base64," in chart_image:
        chart_image = chart_image.split("base64,", 1)[1]

    try:
        msg = _get_vision_llm().invoke([
            SystemMessage(content=_ICT_SYSTEM),
            HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{chart_image}",
                        "detail": "high",
                    },
                },
                {"type": "text", "text": "이 차트를 ICT 관점에서 분석해주세요."},
            ]),
        ])
        logger.info("chart_analysis_node end | session_id=%s", session_id)
        return {"chart_feedback": msg.content}
    except Exception as e:
        logger.warning("chart_analysis_node Vision error: %s", e)
        return {"chart_feedback": f"분석 오류: {e}"}


def feedback_node(state: dict) -> dict:
    """chart_feedback 구조화 → chart_weaknesses를 weaknesses에 병합."""
    session_id = state.get("session_id", "default")
    logger.info("feedback_node start | session_id=%s", session_id)
    chart_feedback = state.get("chart_feedback", "").strip()
    if not chart_feedback or chart_feedback.startswith("분석 오류"):
        logger.info("feedback_node: no valid chart_feedback, skipping")
        return {}

    existing_weaknesses = list(state.get("weaknesses", []))

    try:
        msg = _get_feedback_llm().invoke([
            SystemMessage(content=_FEEDBACK_SYSTEM),
            HumanMessage(content=f"Chart analysis:\n{chart_feedback}"),
        ])
        structured = json.loads(msg.content)
    except Exception as e:
        logger.warning("feedback_node LLM error: %s", e)
        return {}

    chart_weaknesses = structured.get("chart_weaknesses", [])
    merged = existing_weaknesses + [w for w in chart_weaknesses if w not in existing_weaknesses]

    messages = list(state.get("messages", []))
    improvement = structured.get("improvement", "")
    if improvement:
        messages.append({"role": "assistant", "content": improvement})

    logger.info("feedback_node end | session_id=%s merged_weaknesses=%d", session_id, len(merged))
    return {
        "weaknesses": merged,
        "messages":   messages,
    }
