import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import (
    WIN_RATE_THRESHOLD,
    MAX_DRAWDOWN_THRESHOLD,
    AVG_RETURN_RATE_THRESHOLD,
    EXPECTED_VALUE_THRESHOLD,
    LOSS_CONSISTENCY_THRESHOLD,
)
from tools.concept_tool import search_ict_concept, CONCEPT_NOT_FOUND_PREFIX

logger = logging.getLogger(__name__)

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

  win_rate:         float 0.0-1.0  (winning trades / total trades)
  avg_return_rate:  float          (average return rate %; mean of closed_pnl/exec_value*100 per trade; 0.0 if exec_value absent)
  expected_value:   float          (win_rate × avg_win_return% − (1−win_rate) × avg_loss_return%; where avg_loss_return% is mean of abs(return%) for losing trades)
  loss_consistency: float          (std(loss_returns%) / mean(abs(loss_returns%)); 0.0 if fewer than 2 losses; lower = more disciplined stops)
  max_drawdown:     int            (maximum consecutive losing trades)
  best_setup:       str            (setup name with highest avg_return_rate; "" if unavailable)
  worst_setup:      str            (setup name with lowest avg_return_rate; "" if unavailable)
  trade_count:      int            (total number of trades parsed)
  setup_analysis:   object         (per-setup avg_return_rate dict, e.g. {"FVG": 1.2, "OB": -0.5}; {} if setup column absent)
  action_rule:      str            (one concrete rule to apply tomorrow, in Korean, as a prohibition or requirement)

Calculation rules:
- avg_return_rate: mean(closed_pnl / exec_value * 100). If exec_value column is absent or 0, use 0.0.
- expected_value: (win_rate * avg_win_return%) - ((1 - win_rate) * avg_loss_return%)
- loss_consistency: std(loss_return_values) / mean(abs(loss_return_values)). Return 0.0 if < 2 losses.
- setup_analysis values must be avg_return_rate per setup, not win_rate."""

_WEAKNESS_RULES = [
    ("win_rate",         lambda v: v < WIN_RATE_THRESHOLD,            "승률_낮음"),
    ("avg_return_rate",  lambda v: v < AVG_RETURN_RATE_THRESHOLD,     "수익률_낮음"),
    ("expected_value",   lambda v: v < EXPECTED_VALUE_THRESHOLD,      "기대값_음수"),
    ("loss_consistency", lambda v: v > LOSS_CONSISTENCY_THRESHOLD,    "손절_불규칙"),
    ("max_drawdown",     lambda v: v >= MAX_DRAWDOWN_THRESHOLD,       "연속손실_패턴"),
]


def _bybit_trades_to_text(raw_trades: list[dict]) -> str:
    """Bybit 체결 목록을 LLM 분석용 텍스트로 변환."""
    lines = ["date,result,setup,closed_pnl,exec_value"]
    for t in raw_trades:
        try:
            pnl = float(t.get("closedPnl", "0"))
        except (ValueError, TypeError):
            pnl = 0.0
        if pnl == 0.0:
            continue
        result = "win" if pnl > 0 else "loss"
        try:
            import pandas as _pd
            date_str = _pd.to_datetime(int(t.get("execTime", "0")), unit="ms").strftime("%Y-%m-%d")
        except Exception:
            date_str = ""
        try:
            exec_value = float(t.get("execValue", "0"))
        except (ValueError, TypeError):
            exec_value = 0.0
        symbol = t.get("symbol", "")
        setup = symbol.replace("USDT", "").replace("PERP", "").strip()
        lines.append(f"{date_str},{result},{setup},{pnl},{exec_value}")
    return "\n".join(lines)


def journal_analysis_node(state: dict) -> dict:
    """CSV 또는 Bybit JSON 파싱 + OpenAI로 트레이드 통계 산출."""
    session_id = state.get("session_id", "default")
    logger.info("journal_analysis_node start | session_id=%s", session_id)

    raw_trades: list[dict] = state.get("raw_trades", [])
    journal_data: str = state.get("journal_data", "")

    if raw_trades:
        content = _bybit_trades_to_text(raw_trades)
        logger.info("journal_analysis_node: using raw_trades (%d records) | session_id=%s", len(raw_trades), session_id)
    else:
        content = journal_data
        logger.info("journal_analysis_node: using journal_data (CSV) | session_id=%s", session_id)

    try:
        msg = _get_llm().invoke([
            SystemMessage(content=_ANALYSIS_SYSTEM),
            HumanMessage(content=f"Trading journal:\n{content}"),
        ])
        stats = json.loads(msg.content)
    except Exception as e:
        logger.warning("journal_analysis_node LLM error: %s", e)
        stats = {"error": str(e)}
    logger.info("journal_analysis_node end | session_id=%s stats_keys=%s", session_id, list(stats.keys()))
    return {
        "stats":          stats,
        "setup_analysis": stats.get("setup_analysis", {}),
        "action_rule":    stats.get("action_rule", ""),
    }


def weakness_detect_node(state: dict) -> dict:
    """stats 임계값 + past_weaknesses 교차 분석으로 weakness 태그 추출."""
    session_id = state.get("session_id", "default")
    logger.info("weakness_detect_node start | session_id=%s", session_id)
    stats = state.get("stats", {})
    past  = state.get("past_weaknesses", [])

    if "error" in stats:
        logger.warning("weakness_detect_node: stats contains error, skipping detection")
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
    weaknesses = recurring + new_ones

    messages = list(state.get("messages", []))
    concept_not_found = False
    if weaknesses:
        concept_info = search_ict_concept.invoke({"weakness_tag": weaknesses[0]})
        if concept_info.startswith(CONCEPT_NOT_FOUND_PREFIX):
            concept_not_found = True
        else:
            messages.append(AIMessage(content=concept_info))

    logger.info("weakness_detect_node end | session_id=%s weaknesses=%s", session_id, weaknesses)
    return {"weaknesses": weaknesses, "messages": messages, "concept_not_found": concept_not_found}
