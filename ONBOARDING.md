# TradeCoach v2.0 — 프로젝트 컨텍스트

## 프로젝트 개요

AI 기반 트레이딩 코치 에이전트. Bybit API로 매매내역을 자동 수집하고 KPI 분석 → ICT 코칭 → 세션 메모리 루프를 제공하는 LangGraph 파이프라인.

- **현재 브랜치:** `feature/v2.0-stabilization`
- **상태:** v2.0 MVP 완성, 안정화 완료

---

## 실제 파일 구조

```
trade-coach/
├── graph.py              # TradeCoachState(TypedDict) + LangGraph 그래프 정의 + 라우팅 함수
├── config.py             # 환경 변수 / 모델 설정
├── db.py                 # SQLite 초기화 + get_db() 컨텍스트 매니저
├── streamlit_app.py      # Streamlit UI (graph.invoke 호출)
├── final_notebook.ipynb  # QA/테스트용 노트북 (graph.py import해서 실행) — 수정 금지
├── nodes/
│   ├── analysis_nodes.py    # journal_analysis_node, weakness_detect_node
│   ├── chart_nodes.py       # chart_analysis_node, feedback_node
│   ├── coaching_nodes.py    # backtest_coach_node, fallback_classify_node
│   ├── fetch_nodes.py       # new_data_check_node, bybit_fetch_node
│   ├── journal_nodes.py     # journal_write_node
│   ├── memory_nodes.py      # memory_save_node
│   ├── performance_nodes.py # performance_analysis_node
│   ├── preprocess_nodes.py  # preprocess_node
│   └── quiz_nodes.py        # quiz_generate_node, evaluate_quiz()
├── tools/
│   ├── concept_tool.py      # ICT 개념 사전 조회 LangChain tool
│   └── ict_concepts.json    # ICT 개념 25개 정의
├── data/
│   └── sample_trades.json   # Bybit API 없을 때 사용하는 샘플 데이터
└── docs/                    # 설계 문서 (.docx)
```

> `state.py`는 없음 — TradeCoachState는 `graph.py` 안에 정의됨

---

## LangGraph 파이프라인 흐름

```
START
  → memory_load        # DB에서 과거 약점/이력 로드
  → new_data_check     # 새 체결 데이터 있는지 확인
  → [has_new] bybit_fetch → preprocess → journal_write
    → journal_analysis → performance_analysis → weakness_detect
    → [concept_not_found] fallback_classify → backtest_coach
    → [직접] backtest_coach
    → quiz_generate → memory_save → END
  → [no_new] END
```

---

## State 핵심 필드 (TradeCoachState)

| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | str | 세션 식별자 |
| `input_type` | str | `'bybit'` \| `'journal'` \| `'chart'` |
| `stats` | dict | win_rate, avg_return_rate, expected_value, loss_consistency |
| `weaknesses` | list | 현재 세션 약점 태그 |
| `coaching_output` | str | ICT 코칭 결과 텍스트 |
| `quiz_question` | str | 퀴즈 문항 |
| `action_rule` | str | 내일 실행할 규칙 1개 |
| `raw_trades` | list | Bybit API 원본 체결 목록 |
| `journal_entries` | list | 거래별 매매일지 |

---

## DB 스키마 (SQLite: tradecoach.db)

- `trade_history`: 세션별 KPI 저장
- `weaknesses`: 세션별 약점 태그 누적
- `journal_entries`: 거래별 일지 저장

---

## 작업 규칙

- **기준 파일:** `graph.py` + `nodes/*.py` (실제 로직이 모두 여기에 있음)
- **수정 금지:** `final_notebook.ipynb` (QA 노트북)
- 노드 파일에 logger 적용 필수
- 작업 완료 후 `git add -A && git commit`

### 커밋 컨벤션
- `feat:` 새 기능
- `fix:` 버그 수정
- `refactor:` 기능 변경 없는 개선
- `docs:` 문서 수정

---

## streamlit_app ↔ final_notebook 관계

둘 다 동일한 `graph.py` + `nodes/*.py`를 import해서 사용함. 버전 차이 없음.

```
graph.py + nodes/*.py  ← 실제 로직
       ↑                      ↑
final_notebook.ipynb    streamlit_app.py
(테스트/QA)             (UI 앱)
```

---

## 환경 설정

`.env` 파일 필요 (`.env.example` 참고):
- `OPENAI_API_KEY` — 필수
- `BYBIT_API_KEY` / `BYBIT_API_SECRET` — 선택 (없으면 샘플 데이터 모드)

---

## 실행 방법

```bash
# 의존성 설치
uv venv && source .venv/bin/activate && uv sync

# Streamlit UI
streamlit run streamlit_app.py

# 노트북 (QA/테스트)
jupyter notebook final_notebook.ipynb
```

---

## 다음 단계 (v2.1+)

| 버전 | 목표 | 브랜치 |
|------|------|--------|
| v2.1 | Replay Foundation — 거래 시점 캔들 복원 | `feature/replay-foundation` |
| v2.2 | ICT Detector — FVG/OB/MSS 자동 탐지 | `feature/ict-detector-engine` |
| v2.3 | Replay Coach — candle-by-candle 복기 | `feature/replay-coach` |
| v3.0 | A+ Setup Memory — 우수 셋업 라이브러리 | `feature/aplus-setup-memory` |

v2.0을 `main`에 머지 후 다음 브랜치 시작.
