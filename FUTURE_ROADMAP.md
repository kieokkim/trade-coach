# TradeCoach — Future Roadmap

> 현재 브랜치(`feature/v2.0-stabilization`)는 안정화 및 릴리즈 목적입니다.
> v2.1 이후 기능은 별도 브랜치에서 단계적으로 개발합니다.

---

## 왜 현재 브랜치에서 구현하지 않는가

현재 v2.0의 목표는 **"작동 가능한 MVP 안정화"** 입니다.

Replay, ICT 탐지, 차트 복기 기능은 아래 이유로 다음 브랜치에서 진행합니다:

- 기존 LangGraph 파이프라인 구조를 크게 변경해야 함
- OHLCV 데이터 수집/저장 인프라가 현재 없음
- rule-based ICT 탐지 엔진은 독립 모듈로 설계해야 테스트 가능
- MVP를 깨뜨리지 않는 방향 우선

---

## 단계별 로드맵

### v2.0 — MVP 안정화 (현재)

**목표:** 작동 가능한 트레이딩 코치 완성

**구현 완료:**
- Bybit API 거래내역 자동 수집
- KPI 계산 (승률 / 평균 수익률 / 기대값 / 손절 일관성)
- ICT 개념 기반 약점 코칭 (25개 사전)
- SQLite 세션 간 메모리
- LangGraph 기반 코칭 플로우
- Streamlit UI

**브랜치:** `feature/v2.0-stabilization` → `main` 머지

---

### v2.1 — Replay Foundation

**목표:** 거래 시점의 시장 데이터를 복원할 수 있는 기반 구축

**추가 예정:**
- OHLCV Loader (symbol + entry_time 기반 캔들 조회)
- 거래 전후 market context 확보
- 차트 데이터 저장 구조 설계

**신규 모듈:**
```
market/
├── loader.py      # OHLCV 데이터 로더
├── candles.py     # 캔들 조회/저장
└── context.py     # 거래 전후 컨텍스트
```

**주의:** 이 단계에서는 ICT 해석/Replay UI 구현하지 않음

**브랜치:** `feature/replay-foundation`

---

### v2.2 — ICT Detector Engine

**목표:** ICT 패턴 자동 탐지 엔진 구축

**추가 예정:**
- FVG (Fair Value Gap) 탐지
- Order Block 탐지
- MSS / BOS 탐지
- Liquidity Sweep 탐지

**핵심 원칙:**
> 초기 구현은 반드시 **deterministic rule-based 방식 우선**
> LLM 기반 차트 해석 최소화

**신규 모듈:**
```
ict/
├── fvg_detector.py
├── ob_detector.py
├── liquidity.py
└── mss.py
```

**브랜치:** `feature/ict-detector-engine`

---

### v2.3 — Replay Coach

**목표:** 실제 복기 코칭 기능 도입

**추가 예정:**
- 차트 Replay (candle-by-candle 리뷰)
- 진입 근거 질문
- AI 복기 피드백

**예시 코칭:**
> "왜 MSS 확인 전에 진입했나요?"
> "손절을 왜 liquidity 내부에 두었나요?"

**브랜치:** `feature/replay-coach`

---

### v3 — A+ Setup Memory

**목표:** 개인별 우수 셋업 라이브러리 구축

**추가 예정:**
- 좋은 진입 / 나쁜 진입 비교 분석
- 상위 성과 셋업 저장 및 검색
- 개인별 패턴 유사도 분석
- 반복 약점 장기 추적

**예시:**
> "이번 진입은 과거 A+ 셋업 대비 OB retest 확인이 부족했습니다."

**브랜치:** `feature/aplus-setup-memory`

---

## 아키텍처 변화 방향

```
v2.0 (현재)                    v2.1+
───────────────                ───────────────────────────
Bybit API                      Bybit API
  ↓                              ↓
거래내역 수집                  거래내역 수집
  ↓                              ↓
KPI 분석                       KPI 분석
  ↓                              ↓
ICT 코칭                       OHLCV 복원 ← 신규
  ↓                              ↓
결과 저장                      ICT 패턴 탐지 ← 신규
                                 ↓
                               Replay 코칭 ← 신규
                                 ↓
                               A+ 셋업 저장 ← 신규
```

---

## 개발 원칙

1. 현재 MVP를 깨뜨리지 않는 방향 우선
2. 각 버전은 독립 브랜치에서 개발 후 main 머지
3. 차트 해석은 초기엔 rule-based 우선, LLM은 설명/코칭 역할 중심
4. 복기 기능은 "전략 자동매매"보다 "트레이더 행동 교정"에 집중
