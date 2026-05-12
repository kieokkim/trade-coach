import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

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


_PERF_SYSTEM = """\
You are a trading performance analyst. Given current session stats and historical improvement_log, return a JSON object.

Return exactly this structure:
{
  "win_rate":              float,
  "avg_return_rate":       float,
  "expected_value":        float,
  "loss_consistency":      float,
  "max_drawdown":          int,
  "win_rate_trend":        "↑" | "↓" | "→",
  "avg_return_rate_trend": "↑" | "↓" | "→",
  "expected_value_trend":  "↑" | "↓" | "→",
  "best_setup":            str,
  "worst_setup":           str,
  "best_setup_return":     float,
  "worst_setup_return":    float,
  "summary_ko":            str
}

Trend rules (compare current vs most recent previous session in improvement_log):
- win_rate_trend:        ↑ if current > prev, ↓ if current < prev, → if no prev or diff < 0.01
- avg_return_rate_trend: ↑ if current > prev (prev field may be avg_rr or avg_return_rate), ↓ if lower, → if no prev
- expected_value_trend:  ↑ if current > prev, ↓ if lower, → if no prev
- → when no improvement_log or no matching previous field
- best_setup_return / worst_setup_return: avg_return_rate of that setup from setup_analysis (0.0 if absent)
- summary_ko: one Korean sentence summarizing the overall performance trend"""


def performance_analysis_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("performance_analysis_node start | session_id=%s", session_id)

    stats: dict = state.get("stats", {})
    improvement_log: list = state.get("improvement_log", [])

    if "error" in stats or not stats:
        logger.warning("performance_analysis_node: no valid stats, returning empty summary")
        return {"performance_summary": {}}

    prev = improvement_log[0] if improvement_log else {}
    setup_analysis: dict = stats.get("setup_analysis", {})

    payload = {
        "current_stats": {
            "win_rate":        stats.get("win_rate", 0.0),
            "avg_return_rate": stats.get("avg_return_rate", 0.0),
            "expected_value":  stats.get("expected_value", 0.0),
            "loss_consistency": stats.get("loss_consistency", 0.0),
            "max_drawdown":    stats.get("max_drawdown", 0),
            "best_setup":      stats.get("best_setup", ""),
            "worst_setup":     stats.get("worst_setup", ""),
            "setup_analysis":  setup_analysis,
        },
        "previous_session": prev,
    }

    try:
        msg = _get_llm().invoke([
            SystemMessage(content=_PERF_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ])
        performance_summary = json.loads(msg.content)
    except Exception as e:
        logger.warning("performance_analysis_node LLM error: %s | session_id=%s", e, session_id)
        performance_summary = _build_fallback_summary(stats, prev, setup_analysis)

    logger.info("performance_analysis_node end | session_id=%s", session_id)
    return {"performance_summary": performance_summary}


def _build_fallback_summary(stats: dict, prev: dict, setup_analysis: dict) -> dict:
    def trend(cur: float, prev_val: float | None, higher_is_better: bool = True) -> str:
        if prev_val is None:
            return "→"
        diff = cur - prev_val
        if abs(diff) < 0.01:
            return "→"
        if higher_is_better:
            return "↑" if diff > 0 else "↓"
        return "↑" if diff < 0 else "↓"

    prev_rr = prev.get("avg_return_rate") or prev.get("avg_rr")
    best = stats.get("best_setup", "")
    worst = stats.get("worst_setup", "")

    return {
        "win_rate":              stats.get("win_rate", 0.0),
        "avg_return_rate":       stats.get("avg_return_rate", 0.0),
        "expected_value":        stats.get("expected_value", 0.0),
        "loss_consistency":      stats.get("loss_consistency", 0.0),
        "max_drawdown":          stats.get("max_drawdown", 0),
        "win_rate_trend":        trend(stats.get("win_rate", 0.0), prev.get("win_rate")),
        "avg_return_rate_trend": trend(stats.get("avg_return_rate", 0.0), prev_rr),
        "expected_value_trend":  trend(stats.get("expected_value", 0.0), prev.get("expected_value")),
        "best_setup":            best,
        "worst_setup":           worst,
        "best_setup_return":     setup_analysis.get(best, 0.0),
        "worst_setup_return":    setup_analysis.get(worst, 0.0),
        "summary_ko":            "",
    }
