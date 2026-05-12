import base64
import os

import pandas as pd
import streamlit as st

from graph import DEFAULT_STATE, graph

st.set_page_config(page_title="TradeCoach", page_icon="📊", layout="wide")

# ──────────────────── 앱 시작 시 DB에서 이전 결과 복원 ─────────────────────

if "last_stats" not in st.session_state:
    try:
        from db import get_db
        _sid = st.session_state.get("session_id", "default")
        with get_db() as conn:
            row = conn.execute(
                """SELECT win_rate, avg_return_rate, expected_value,
                          loss_consistency, action_rule
                   FROM trade_history
                   WHERE session_id=? ORDER BY date DESC LIMIT 1""",
                (_sid,),
            ).fetchone()
        if row:
            st.session_state["last_stats"] = {
                "win_rate":        row["win_rate"] or 0.0,
                "avg_return_rate": row["avg_return_rate"] or 0.0,
                "expected_value":  row["expected_value"] or 0.0,
                "loss_consistency": row["loss_consistency"] or 0.0,
            }
            st.session_state["last_action_rule"] = row["action_rule"] or ""
    except Exception:
        pass

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
        st.session_state["last_result"]     = result
        st.session_state["last_stats"]      = result.get("stats", {})
        st.session_state["last_weaknesses"] = result.get("weaknesses", [])
        st.session_state["last_action_rule"] = result.get("action_rule", "")
        st.session_state["last_setup"]      = result.get("setup_analysis", {})
        st.session_state["last_coaching"]   = result.get("coaching_output", "")

    # 사이드바 분석 결과 미리보기
    if "last_action_rule" in st.session_state and st.session_state["last_action_rule"]:
        st.success(st.session_state["last_action_rule"])

    st.divider()

    # 마지막 세션 요약
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
        st.session_state["last_result"]      = result
        st.session_state["last_stats"]       = result.get("stats", {})
        st.session_state["last_weaknesses"]  = result.get("weaknesses", [])
        st.session_state["last_action_rule"] = result.get("action_rule", "")
        st.session_state["last_setup"]       = result.get("setup_analysis", {})
        st.session_state["last_coaching"]    = result.get("coaching_output", "")

    # 결과는 session_state에서 표시 (새로고침 후에도 유지)
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
            df = pd.DataFrame(
                list(setup_analysis.items()),
                columns=["셋업", "평균 수익률 (%)"],
            ).set_index("셋업")
            st.bar_chart(df)

        coaching = st.session_state.get("last_coaching", "")
        if coaching:
            st.subheader("💬 코칭 피드백")
            st.write(coaching)

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

        # improvement_log
        improvement_log = res.get("improvement_log", [])
        st.subheader("📅 세션별 개선 이력")
        if improvement_log:
            df_log = pd.DataFrame(improvement_log)
            st.dataframe(df_log, use_container_width=True)
        else:
            st.caption("저장된 이력 없음 (첫 세션이거나 memory_save 미실행)")

        # performance_summary
        performance_summary = res.get("performance_summary", {})
        st.subheader("📊 성과 요약 (현재 세션)")
        if performance_summary:
            st.json(performance_summary)
        else:
            st.caption("성과 요약 없음")
