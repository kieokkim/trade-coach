from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from db import get_db, init_db
from nodes.analysis_nodes import journal_analysis_node, weakness_detect_node
from nodes.chart_nodes import chart_analysis_node, feedback_node
from nodes.coaching_nodes import backtest_coach_node, fallback_classify_node
from nodes.fetch_nodes import new_data_check_node, bybit_fetch_node
from nodes.journal_nodes import journal_write_node
from nodes.memory_nodes import memory_save_node
from nodes.quiz_nodes import quiz_generate_node
from nodes.performance_nodes import performance_analysis_node
from nodes.preprocess_nodes import preprocess_node

load_dotenv()
init_db()

# ──────────────────────────────── State ────────────────────────────────────

class TradeCoachState(TypedDict, total=False):
    session_id:      str
    input_type:      str          # 'journal' | 'chart' | 'both'
    journal_data:    str          # CSV 원문
    chart_image:     str          # base64 인코딩 이미지
    stats:           dict         # 승률/손익비/드로다운 등
    weaknesses:      list         # 현재 세션 약점 태그
    past_weaknesses: list         # DB 로드 과거 약점
    chart_feedback:  str          # 차트 분석 결과 텍스트
    current_concept: str          # 현재 학습 중인 개념
    quiz_question:   str          # 퀴즈 문항
    quiz_answer:     str          # 사용자 답변
    quiz_result:     str          # 'pass' | 'fail' | ''
    retry_count:     int          # 퀴즈 재시도 횟수
    trade_count:     int          # 총 분석 트레이드 수
    improvement_log: list         # 세션별 실력 변화
    messages:        list         # 대화 히스토리
    setup_analysis:    dict       # 셋업별 수익률 딕셔너리
    action_rule:       str        # 내일 실행할 규칙 1개
    avg_return_rate:   float      # 평균 수익률 %
    expected_value:    float      # 기대값 %
    loss_consistency:  float      # 손절 일관성 (낮을수록 규율 있음)
    concept_not_found: bool       # fallback 라우팅 플래그
    last_fetched_at: str          # ISO datetime, 마지막 Bybit 수집 시각
    has_new_data:    bool         # 새 체결 데이터 존재 여부
    raw_trades:      list         # Bybit API 원본 체결 목록
    journal_entries: list         # 거래별 매매일지
    performance_summary: dict     # 성과 요약 KPI
    coaching_output: str          # ICT 코칭 결과 텍스트
    fallback_type:   str          # 'ict' | 'psychology' | 'pattern' | ''


DEFAULT_STATE: TradeCoachState = {
    "session_id":        "default",
    "input_type":        "",
    "journal_data":      "",
    "chart_image":       "",
    "stats":             {},
    "weaknesses":        [],
    "past_weaknesses":   [],
    "chart_feedback":    "",
    "current_concept":   "",
    "quiz_question":     "",
    "quiz_answer":       "",
    "quiz_result":       "",
    "retry_count":       0,
    "trade_count":       0,
    "improvement_log":   [],
    "messages":          [],
    "setup_analysis":    {},
    "action_rule":       "",
    "avg_return_rate":   0.0,
    "expected_value":    0.0,
    "loss_consistency":  0.0,
    "concept_not_found": False,
    "last_fetched_at":   "",
    "has_new_data":      False,
    "raw_trades":        [],
    "journal_entries":   [],
    "performance_summary": {},
    "coaching_output":   "",
    "fallback_type":     "",
}

# ──────────────────────────────── Nodes ────────────────────────────────────

def memory_load_node(state: TradeCoachState) -> dict:
    session_id = state.get("session_id", "default")
    past_weaknesses, trade_count, improvement_log = [], 0, []
    last_fetched_at = ""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT weakness FROM weaknesses WHERE session_id = ? ORDER BY count DESC",
                (session_id,),
            ).fetchall()
            past_weaknesses = [r["weakness"] for r in rows]

            count_row = conn.execute(
                "SELECT COALESCE(SUM(trade_count), 0) FROM trade_history WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            trade_count = int(count_row[0]) if count_row else 0

            history_rows = conn.execute(
                "SELECT date, win_rate, avg_return_rate, expected_value, loss_consistency"
                " FROM trade_history"
                " WHERE session_id = ? ORDER BY date DESC LIMIT 10",
                (session_id,),
            ).fetchall()
            improvement_log = [dict(r) for r in history_rows]

            lf_row = conn.execute(
                "SELECT last_fetched_at FROM trade_history"
                " WHERE session_id = ? AND last_fetched_at IS NOT NULL"
                " ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if lf_row:
                last_fetched_at = lf_row["last_fetched_at"] or ""
    except Exception:
        pass
    return {
        "past_weaknesses": past_weaknesses,
        "trade_count":     trade_count,
        "improvement_log": improvement_log,
        "last_fetched_at": last_fetched_at,
    }


def input_router_node(state: TradeCoachState) -> dict:
    has_journal = bool(state.get("journal_data", "").strip())
    has_chart   = bool(state.get("chart_image",  "").strip())
    if has_journal and has_chart:
        input_type = "both"
    elif has_chart:
        input_type = "chart"
    else:
        input_type = "journal"
    return {"input_type": input_type}

# ──────────────────────────────── Routing ──────────────────────────────────

def route_after_input(state: TradeCoachState) -> str:
    return state["input_type"]


def route_new_data(state: TradeCoachState) -> str:
    return "has_new" if state.get("has_new_data", False) else "no_new"


def route_after_weakness(state: TradeCoachState) -> str:
    if state.get("concept_not_found"):
        return "fallback_classify"
    return "backtest_coach"


def route_after_fallback(state: TradeCoachState) -> str:
    return "backtest_coach"

# ──────────────────────────────── Graph ────────────────────────────────────

def _build_graph() -> StateGraph:
    builder = StateGraph(TradeCoachState)

    builder.add_node("memory_load",          memory_load_node)
    builder.add_node("new_data_check",       new_data_check_node)
    builder.add_node("bybit_fetch",          bybit_fetch_node)
    builder.add_node("preprocess",           preprocess_node)
    builder.add_node("journal_write",        journal_write_node)
    builder.add_node("input_router",         input_router_node)
    builder.add_node("journal_analysis",     journal_analysis_node)
    builder.add_node("performance_analysis", performance_analysis_node)
    builder.add_node("weakness_detect",      weakness_detect_node)
    builder.add_node("fallback_classify",    fallback_classify_node)
    builder.add_node("backtest_coach",       backtest_coach_node)
    builder.add_node("quiz_generate",        quiz_generate_node)
    builder.add_node("memory_save",          memory_save_node)

    builder.add_edge(START, "memory_load")
    builder.add_edge("memory_load", "new_data_check")
    builder.add_conditional_edges(
        "new_data_check",
        route_new_data,
        {"has_new": "bybit_fetch", "no_new": END},
    )
    builder.add_edge("bybit_fetch", "preprocess")
    builder.add_edge("preprocess", "journal_write")
    builder.add_edge("journal_write", "journal_analysis")
    builder.add_edge("journal_analysis", "performance_analysis")
    builder.add_edge("performance_analysis", "weakness_detect")
    builder.add_conditional_edges(
        "weakness_detect",
        route_after_weakness,
        {"fallback_classify": "fallback_classify", "backtest_coach": "backtest_coach"},
    )
    builder.add_conditional_edges(
        "fallback_classify",
        route_after_fallback,
        {"backtest_coach": "backtest_coach"},
    )
    builder.add_edge("backtest_coach", "quiz_generate")
    builder.add_edge("quiz_generate",  "memory_save")
    builder.add_edge("memory_save", END)

    return builder.compile()


graph = _build_graph()
