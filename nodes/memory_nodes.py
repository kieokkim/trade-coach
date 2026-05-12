import logging
from datetime import date, datetime, timezone

from db import get_db

logger = logging.getLogger(__name__)


def memory_save_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("memory_save_node start | session_id=%s", session_id)

    stats: dict = state.get("stats", {})
    weaknesses: list = state.get("weaknesses", [])
    quiz_result: str = state.get("quiz_result", "")
    current_concept: str = state.get("current_concept", "")
    performance_summary: dict = state.get("performance_summary", {})
    action_rule: str = state.get("action_rule", "")
    last_fetched_at: str = state.get("last_fetched_at", "") or datetime.now(tz=timezone.utc).isoformat()

    today = date.today().isoformat()

    try:
        with get_db() as conn:
            # 1. weaknesses 저장 (upsert)
            for weakness in weaknesses:
                conn.execute(
                    """
                    INSERT INTO weaknesses (session_id, weakness, count, last_seen)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(session_id, weakness)
                    DO UPDATE SET count = count + 1, last_seen = excluded.last_seen
                    """,
                    (session_id, weakness, today),
                )

            # 2. quiz_results 저장
            if quiz_result and current_concept:
                conn.execute(
                    "INSERT INTO quiz_results (session_id, concept, passed, retry_count, date) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        session_id, current_concept,
                        quiz_result == "pass",
                        state.get("retry_count", 0),
                        today,
                    ),
                )

            # 3. trade_history 저장 (신규 KPI 3개, avg_rr=0.0 호환 유지)
            if stats and "error" not in stats:
                conn.execute(
                    """
                    INSERT INTO trade_history
                        (session_id, date, win_rate, avg_rr, max_drawdown,
                         main_weakness, trade_count,
                         avg_return_rate, expected_value, loss_consistency, last_fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id, today,
                        stats.get("win_rate", 0.0),
                        0.0,                                      # avg_rr deprecated
                        stats.get("max_drawdown", 0),
                        weaknesses[0] if weaknesses else None,
                        stats.get("trade_count", 0),
                        stats.get("avg_return_rate", 0.0),
                        stats.get("expected_value", 0.0),
                        stats.get("loss_consistency", 0.0),
                        last_fetched_at,
                    ),
                )

            # 4. performance_snapshots 저장
            if performance_summary:
                conn.execute(
                    """
                    INSERT INTO performance_snapshots
                        (session_id, period, period_start,
                         win_rate, avg_return_rate, expected_value, loss_consistency,
                         top_weakness, action_rule)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id, "session", today,
                        performance_summary.get("win_rate", 0.0),
                        performance_summary.get("avg_return_rate", 0.0),
                        performance_summary.get("expected_value", 0.0),
                        performance_summary.get("loss_consistency", 0.0),
                        weaknesses[0] if weaknesses else "",
                        action_rule,
                    ),
                )
    except Exception as e:
        logger.warning("memory_save_node DB error: %s | session_id=%s", e, session_id)

    logger.info("memory_save_node end | session_id=%s weaknesses=%d", session_id, len(weaknesses))
    return {}
