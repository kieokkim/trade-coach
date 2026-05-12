import logging

logger = logging.getLogger(__name__)


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

    summary = _build_summary(stats, prev, setup_analysis)
    logger.info("performance_analysis_node end | session_id=%s", session_id)
    return {"performance_summary": summary}


def _build_summary(stats: dict, prev: dict, setup_analysis: dict) -> dict:
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
    best    = stats.get("best_setup",  "")
    worst   = stats.get("worst_setup", "")
    win_rate = stats.get("win_rate", 0.0)
    avg_rr   = stats.get("avg_return_rate", 0.0)

    return {
        "win_rate":              win_rate,
        "avg_return_rate":       avg_rr,
        "expected_value":        stats.get("expected_value",  0.0),
        "loss_consistency":      stats.get("loss_consistency", 0.0),
        "max_drawdown":          stats.get("max_drawdown", 0),
        "win_rate_trend":        trend(win_rate, prev.get("win_rate")),
        "avg_return_rate_trend": trend(avg_rr, prev_rr),
        "expected_value_trend":  trend(stats.get("expected_value", 0.0), prev.get("expected_value")),
        "best_setup":            best,
        "worst_setup":           worst,
        "best_setup_return":     setup_analysis.get(best,  0.0),
        "worst_setup_return":    setup_analysis.get(worst, 0.0),
        "summary_ko":            _summary_ko(win_rate, avg_rr, prev.get("win_rate")),
    }


def _summary_ko(win_rate: float, avg_rr: float, prev_wr: float | None) -> str:
    if prev_wr is None:
        return f"승률 {win_rate:.1%}, 평균수익률 {avg_rr:.2f}%로 첫 세션을 기록했습니다."
    if win_rate > prev_wr + 0.01:
        trend = "전 세션 대비 승률이 상승했습니다"
    elif win_rate < prev_wr - 0.01:
        trend = "전 세션 대비 승률이 하락했습니다"
    else:
        trend = "전 세션과 승률이 비슷합니다"
    return f"승률 {win_rate:.1%}, 평균수익률 {avg_rr:.2f}%. {trend}."
