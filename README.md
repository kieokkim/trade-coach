# TradeCoach
AI 기반 트레이딩 코치 에이전트.
Bybit API로 매매내역을 자동 수집하고
매매일지 → 성과분석 → ICT 코칭 루프를 제공합니다.

## 핵심 기능
- Bybit API 자동 수집 (없으면 샘플 데이터)
- 신규 KPI: 수익률 / 기대값 / 손절 일관성
- ICT 개념 기반 약점 코칭 (25개 사전)
- SQLite 세션 간 메모리

## 설치 및 실행
```bash
uv venv && source .venv/bin/activate
uv sync
```

### Jupyter
```bash
jupyter notebook final_notebook.ipynb
```

### Streamlit
```bash
streamlit run streamlit_app.py
```

## 환경 설정
`.env` 파일 생성 (`.env.example` 참고)

## 프로젝트 구조
```
trade-coach/
├── graph.py
├── state.py
├── config.py
├── db.py
├── nodes/
├── tools/
├── data/
├── streamlit_app.py
└── final_notebook.ipynb
```

---

## Future Roadmap

TradeCoach는 단순 성과 분석기를 넘어
**AI 기반 트레이딩 저널 + 복기 코치**로 진화합니다.

| 버전 | 목표 | 상태 |
|------|------|------|
| v2.0 | MVP 안정화 (현재) | ✅ 완료 |
| v2.1 | Replay Foundation — 거래 시점 캔들 복원 | 🔜 예정 |
| v2.2 | ICT Detector — FVG/OB/MSS 자동 탐지 | 🔜 예정 |
| v2.3 | Replay Coach — candle-by-candle 복기 코칭 | 🔜 예정 |
| v3.0 | A+ Setup Memory — 개인별 우수 셋업 라이브러리 | 🔜 예정 |

> 위 기능들은 아직 구현되지 않았습니다.
> 현재 지원 기능은 상단 "핵심 기능" 섹션을 참고하세요.

자세한 로드맵은 [FUTURE_ROADMAP.md](./FUTURE_ROADMAP.md)를 참고하세요.

---

## 문서 체계

| 문서 | 역할 | 대상 독자 |
|------|------|---------|
| README.md | 설치/실행 가이드 | 처음 사용자 |
| TRADECOACH_AGENT_OVERVIEW.md | 서비스 상세 소개 | 기능 파악 원하는 사람 |
| FUTURE_ROADMAP.md | v2.1~v3 개발 계획 | 기여자/개발자 |
| NEXT_BRANCH_PLAN.md | 브랜치 전략 | 개발자 |
| docs/01_LangGraph_상세_노드_설계서_v2.1.docx | 노드 설계 명세 | 개발자 |
| docs/04_MVP_API_명세서_v2.1.docx | API/State 명세 | 개발자 |
| docs/05_MVP_DB_스키마_설계서_v2.1.docx | DB 스키마 | 개발자 |
| docs/06_배포후_최소회귀_테스트_체크리스트_v0.3.docx | 배포 체크리스트 | 운영자 |

---

## 문서 체계 전체 구조

### 읽는 순서

```
처음 사용자:
  README.md
    → TRADECOACH_AGENT_OVERVIEW.md

개발 참여:
  README.md
    → docs/09_프로젝트_작업_지침_v2.0.docx
    → docs/01_LangGraph_상세_노드_설계서_v2.1.docx
    → docs/04_MVP_API_명세서_v2.1.docx
    → docs/05_MVP_DB_스키마_설계서_v2.1.docx

차세대 기능 개발:
  FUTURE_ROADMAP.md
    → NEXT_BRANCH_PLAN.md

배포/운영:
  docs/06_배포후_최소회귀_테스트_체크리스트_v0.3.docx
```

### 문서 역할 분리

```
서비스 소개 레이어:
  README.md ──────────────── 설치/실행 (간결)
  AGENT_OVERVIEW.md ───────── 기능 상세 (풍부)

개발 설계 레이어:
  docs/01 노드 설계서 ──────── LangGraph 구조
  docs/04 API 명세서 ──────── State/노드 인터페이스
  docs/05 DB 스키마 ───────── 데이터 구조
  docs/09 작업 지침 ───────── 코딩 원칙/브랜치

개발 전략 레이어:
  FUTURE_ROADMAP.md ──────── v2.1~v3 방향
  NEXT_BRANCH_PLAN.md ────── 브랜치 전략

운영 레이어:
  docs/06 체크리스트 ──────── 배포 검증
  docs/07 개발보고서 ──────── 이력 기록
```
