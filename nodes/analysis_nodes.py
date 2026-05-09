import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _llm

_ANALYSIS_SYSTEM = """\
You are a trading journal analyzer. Parse the trading journal and return JSON with exactly these keys:
  win_rate:     float 0.0-1.0  (winning trades / total trades)
  avg_rr:       float          (average risk:reward ratio; 0.0 if column absent)
  max_drawdown: int            (maximum consecutive losing trades)
  best_setup:   str            (setup/pattern name with highest win rate; "" if unavailable)
  worst_setup:  str            (setup/pattern name with lowest win rate; "" if unavailable)
  trade_count:  int            (total number of trades parsed)"""

_WEAKNESS_RULES = [
    ("win_rate",     lambda v: v < 0.4, "승률_낮음"),
    ("avg_rr",       lambda v: v < 1.5, "손익비_부족"),
    ("max_drawdown", lambda v: v >= 3,  "연속손실_패턴"),
]


def journal_analysis_node(state: dict) -> dict:
    """CSV 파싱 + OpenAI로 트레이드 통계 산출."""
    journal_data = state.get("journal_data", "")
    try:
        msg = _get_llm().invoke([
            SystemMessage(content=_ANALYSIS_SYSTEM),
            HumanMessage(content=f"Trading journal:\n{journal_data}"),
        ])
        stats = json.loads(msg.content)
    except Exception as e:
        stats = {"error": str(e)}
    return {"stats": stats}


def weakness_detect_node(state: dict) -> dict:
    """stats 임계값 + past_weaknesses 교차 분석으로 weakness 태그 추출."""
    stats = state.get("stats", {})
    past  = state.get("past_weaknesses", [])

    if "error" in stats:
        return {"weaknesses": []}

    current: list[str] = []
    for key, check, tag in _WEAKNESS_RULES:
        val = stats.get(key)
        if val is not None and check(val):
            current.append(tag)

    worst = stats.get("worst_setup", "")
    if worst:
        current.append(f"{worst}_개선필요")

    recurring = [w for w in current if w in past]
    new_ones  = [w for w in current if w not in past]
    return {"weaknesses": recurring + new_ones}
