import base64
import os

import pandas as pd
import streamlit as st

from graph import DEFAULT_STATE, graph
from nodes.quiz_nodes import evaluate_quiz

st.set_page_config(page_title="TradeCoach", page_icon="📊", layout="wide")

# ──────────────────── 앱 시작 시 DB에서 이전 결과 복원 ─────────────────────

if "last_stats" not in st.session_state:
    try:
        from db import get_db
        _sid = st.session_state.get("session_id", "default")
        with get_db() as conn:
            row = conn.execute(
                """SELECT win_rate, avg_return_rate, expected_value,
                          loss_consistency
                   FROM trade_history
                   WHERE session_id=? ORDER BY date DESC LIMIT 1""",
                (_sid,),
            ).fetchone()
        if row:
            st.session_state["last_stats"] = {
                "win_rate":         row["win_rate"] or 0.0,
                "avg_return_rate":  row["avg_return_rate"] or 0.0,
                "expected_value":   row["expected_value"] or 0.0,
                "loss_consistency": row["loss_consistency"] or 0.0,
            }
    except Exception:
        pass


def _save_result(result: dict) -> None:
    """graph.invoke 반환값을 session_state에 저장."""
    st.session_state["last_result"]          = result
    st.session_state["last_stats"]           = result.get("stats", {})
    st.session_state["last_weaknesses"]      = result.get("weaknesses", [])
    st.session_state["last_action_rule"]     = result.get("action_rule", "")
    st.session_state["last_setup"]           = result.get("setup_analysis", {})
    st.session_state["last_coaching"]        = result.get("coaching_output", "")
    st.session_state["last_journal_entries"] = result.get("journal_entries", [])
    st.session_state["last_quiz_question"]   = result.get("quiz_question", "")
    st.session_state["last_quiz_concept"]    = result.get("current_concept", "")
    # 새 분석 시작 시 이전 퀴즈 결과 초기화
    st.session_state.pop("last_quiz_result",   None)
    st.session_state.pop("last_quiz_feedback", None)


# ──────────────────────────────── 사이드바 ─────────────────────────────────

with st.sidebar:
    st.title("⚙️ TradeCoach")

    session_id = st.text_input("Session ID", value="default", key="session_id")

    st.divider()

    api_key = os.getenv("BYBIT_API_KEY", "")
    if api_key:
        st.sidebar.success("🔗 Bybit API 연결됨")
    else:
        st.sidebar.info("📂 샘플 데이터 모드")

    if st.button("▶ Bybit 분석 시작", type="primary", key="run_bybit"):
        with st.spinner("Bybit 데이터 수집 및 분석 중..."):
            state = {
                **DEFAULT_STATE,
                "session_id":  session_id,
                "input_type":  "bybit",
                "journal_data": "",
                "raw_trades":  [],
            }
            result = graph.invoke(state)
        _save_result(result)

    if "last_action_rule" in st.session_state and st.session_state["last_action_rule"]:
        st.success(st.session_state["last_action_rule"])

    st.divider()

    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        st.subheader("📋 마지막 세션 요약")
        past_w = res.get("past_weaknesses", [])
        if past_w:
            st.write("**과거 약점**")
            for w in past_w:
                st.caption(f"• {w}")
        else:
            st.caption("과거 약점 없음")
        lf = res.get("last_fetched_at", "")
        st.caption(f"마지막 수집: {lf[:19] if lf else '없음'}")

    st.divider()
    st.caption("TradeCoach v2.0 | feature/v2.0-stabilization")

# ──────────────────────────────── 메인 탭 ──────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📊 저널 분석", "📈 차트 분석", "🗓️ 성과 기록"])

# ══════════════════════════ Tab 1: 저널 분석 ═══════════════════════════════

with tab1:
    st.header("📊 저널 분석")

    sample_csv = """date,result,setup,closed_pnl,exec_value
2026-05-01,win,FVG,15.2,1200
2026-05-02,loss,OB,-8.1,800
2026-05-03,win,FVG,22.4,1500
2026-05-04,loss,FVG,-9.3,900
2026-05-05,win,유동성스윕,31.0,2000"""

    journal_input = st.text_area(
        "매매 일지 CSV 입력",
        value=sample_csv,
        height=200,
        help="date, result, setup 컬럼 필수. closed_pnl/exec_value 있으면 수익률 계산에 활용됩니다.",
    )

    if st.button("▶ 저널 분석 실행", type="primary", key="run_journal"):
        with st.spinner("분석 중..."):
            state = {
                **DEFAULT_STATE,
                "session_id":   session_id,
                "input_type":   "journal",
                "journal_data": journal_input,
                "raw_trades":   [],
            }
            result = graph.invoke(state)
        _save_result(result)

    # ── 결과 표시 (session_state 기반, 새로고침 후에도 유지) ──
    if "last_stats" not in st.session_state:
        st.info("👆 사이드바에서 분석 시작 버튼을 눌러주세요")
    else:
        stats = st.session_state["last_stats"]

        st.subheader("📌 핵심 지표")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("승률",       f"{stats.get('win_rate', 0):.1%}")
        c2.metric("평균 수익률", f"{stats.get('avg_return_rate', 0):.2f}%")
        c3.metric("기대값",      f"{stats.get('expected_value', 0):.2f}%")
        c4.metric("손절 일관성", f"{stats.get('loss_consistency', 0):.2f}")

        weaknesses = st.session_state.get("last_weaknesses", [])
        if weaknesses:
            st.subheader("⚠️ 감지된 약점")
            for w in weaknesses:
                st.info(w)

        action_rule = st.session_state.get("last_action_rule", "")
        if action_rule:
            st.subheader("★ 내일의 규칙")
            st.success(action_rule)

        setup_analysis = st.session_state.get("last_setup", {})
        if setup_analysis:
            st.subheader("📈 셋업별 수익률")
            df_setup = pd.DataFrame(
                list(setup_analysis.items()),
                columns=["셋업", "평균 수익률 (%)"],
            ).set_index("셋업")
            st.bar_chart(df_setup)

        coaching = st.session_state.get("last_coaching", "")
        if coaching:
            st.subheader("💬 코칭 피드백")
            st.write(coaching)

        # ── 매매일지 ──
        journal_entries = st.session_state.get("last_journal_entries", [])
        if journal_entries:
            st.subheader("📒 매매일지")
            for entry in journal_entries:
                label = (
                    f"{entry.get('date', '')} | "
                    f"{entry.get('symbol', '')} | "
                    f"{'✅ 승' if entry.get('result') == 'win' else '❌ 패'}"
                )
                with st.expander(label):
                    st.write(f"**진입 근거**: {entry.get('entry_reason', '') or '추론 불가'}")
                    st.write(f"**청산 근거**: {entry.get('exit_reason', '') or '추론 불가'}")
                    st.write(f"**회고**: {entry.get('reflection', '') or '-'}")

        # ── 퀴즈 (코칭 직후) ──
        quiz_question = st.session_state.get("last_quiz_question", "")
        if quiz_question:
            st.divider()
            st.subheader("🧠 개념 확인 퀴즈")
            st.write(f"**{quiz_question}**")

            quiz_result = st.session_state.get("last_quiz_result", "")

            if not quiz_result:
                quiz_answer = st.text_input(
                    "답변을 입력하세요",
                    key="quiz_answer_input",
                    placeholder="자유롭게 답변해주세요",
                )
                if st.button("📝 답변 제출", key="submit_quiz"):
                    if quiz_answer.strip():
                        with st.spinner("답변 평가 중..."):
                            result, feedback = evaluate_quiz(
                                session_id=session_id,
                                quiz_question=quiz_question,
                                quiz_answer=quiz_answer,
                                current_concept=st.session_state.get("last_quiz_concept", ""),
                                retry_count=st.session_state.get("quiz_retry_count", 0),
                            )
                        st.session_state["last_quiz_result"]   = result
                        st.session_state["last_quiz_feedback"] = feedback
                        st.rerun()
                    else:
                        st.warning("답변을 입력해주세요.")
            else:
                feedback = st.session_state.get("last_quiz_feedback", "")
                if quiz_result == "pass":
                    st.success(f"✅ 정답! {feedback}")
                else:
                    st.error(f"❌ 다시 생각해보세요. {feedback}")
                    if st.button("🔄 다시 시도", key="retry_quiz"):
                        retry = st.session_state.get("quiz_retry_count", 0) + 1
                        st.session_state["quiz_retry_count"] = retry
                        st.session_state.pop("last_quiz_result",   None)
                        st.session_state.pop("last_quiz_feedback", None)
                        st.rerun()

# ══════════════════════════ Tab 2: 차트 분석 ═══════════════════════════════

with tab2:
    st.header("📈 차트 분석")

    uploaded = st.file_uploader(
        "차트 이미지 업로드",
        type=["png", "jpg", "jpeg"],
        help="ICT 기반 차트 분석을 수행합니다.",
    )

    if uploaded:
        st.image(uploaded, caption="업로드된 차트", use_container_width=True)

    if st.button("▶ 차트 분석 실행", type="primary", key="run_chart", disabled=not uploaded):
        with st.spinner("차트 분석 중..."):
            img_b64 = base64.b64encode(uploaded.read()).decode()
            state = {
                **DEFAULT_STATE,
                "session_id":  session_id,
                "chart_image": img_b64,
            }
            result = graph.invoke(state)

        st.session_state["last_result"] = result
        feedback = result.get("chart_feedback", "")
        if feedback:
            st.subheader("🔍 차트 분석 결과")
            st.write(feedback)
        else:
            st.info("차트 피드백이 생성되지 않았습니다. 그래프 라우팅을 확인하세요.")

# ══════════════════════════ Tab 3: 성과 기록 ═══════════════════════════════

with tab3:
    st.header("🗓️ 성과 기록")

    if "last_result" not in st.session_state:
        st.info("Tab 1 또는 Tab 2에서 먼저 분석을 실행하세요.")
    else:
        res = st.session_state["last_result"]

        improvement_log = res.get("improvement_log", [])
        st.subheader("📅 세션별 개선 이력")
        if improvement_log:
            df_log = pd.DataFrame(improvement_log)
            st.dataframe(df_log, use_container_width=True)
        else:
            st.caption("저장된 이력 없음 (첫 세션이거나 memory_save 미실행)")

        performance_summary = res.get("performance_summary", {})
        st.subheader("📊 성과 요약 (현재 세션)")
        if performance_summary:
            st.json(performance_summary)
        else:
            st.caption("성과 요약 없음")
