# TradeCoach — Next Branch Plan

> D8 완료 이후 신규 브랜치 전략 정리

---

## 현재 브랜치 역할

| 브랜치 | 역할 | 상태 |
|--------|------|------|
| `main` | v1.x MVP 안정 버전 | 유지 |
| `feature/v2.0-stabilization` | v2.0 안정화 및 릴리즈 | **현재 작업 중** |

---

## v2.0 안정화 완료 절차

D8 작업이 완료되면 아래 순서로 진행합니다:

```bash
# 1. 최종 커밋 + 태그
git add -A
git commit -m "feat: TradeCoach v2.0 완성"
git tag v2.0

# 2. main 브랜치로 머지
git checkout main
git merge feature/v2.0-stabilization

# 3. 푸시
git push origin main --tags
```

---

## 신규 브랜치 생성 이유

v2.0 안정화 이후 기능들은 현재 구조를 크게 변경합니다:

- **OHLCV 데이터 인프라** — 새로운 모듈(`market/`) 추가 필요
- **ICT 탐지 엔진** — 독립 모듈(`ict/`)로 설계해야 테스트 가능
- **Replay UI** — Streamlit 구조 대규모 변경 필요

이런 변경을 `main`에서 직접 하면 v2.0 안정성이 깨집니다.
따라서 기능별 독립 브랜치에서 개발 후 검증된 것만 머지합니다.

---

## 추천 브랜치 전략

### v2.1 — Replay Foundation

```bash
git checkout main
git checkout -b feature/replay-foundation
```

**작업 범위:**
- `market/loader.py` — OHLCV 데이터 로더
- `market/candles.py` — symbol + entry_time 기반 캔들 조회
- `market/context.py` — 거래 전후 market context
- DB 스키마 확장 (candles 테이블)

**완료 기준:**
- 거래 1건의 entry_time으로 전후 20개 캔들 조회 가능
- 캔들 데이터 DB 저장/조회 가능

---

### v2.2 — ICT Detector Engine

```bash
git checkout feature/replay-foundation
git checkout -b feature/ict-detector-engine
```

**작업 범위:**
- `ict/fvg_detector.py` — FVG 탐지
- `ict/ob_detector.py` — Order Block 탐지
- `ict/liquidity.py` — Liquidity Sweep 탐지
- `ict/mss.py` — MSS / BOS 탐지

**핵심 원칙:**
> 초기 구현은 반드시 rule-based 방식 우선
> LLM은 탐지 결과 설명/코칭에만 사용

**완료 기준:**
- 샘플 캔들 데이터에서 FVG / OB / MSS 각각 탐지 성공
- 단위 테스트 통과

---

### v2.3 — Replay Coach

```bash
git checkout feature/ict-detector-engine
git checkout -b feature/replay-coach
```

**작업 범위:**
- Streamlit Replay UI (candle-by-candle)
- 진입 근거 질문 플로우
- AI 복기 피드백 노드

**완료 기준:**
- 거래 1건 선택 → 차트 표시 → AI 질문 → 피드백 전체 플로우 작동

---

### v3 — A+ Setup Memory

```bash
git checkout main  # v2.3 머지 후
git checkout -b feature/aplus-setup-memory
```

**작업 범위:**
- 우수 셋업 저장/검색 DB
- 과거 셋업과 현재 진입 유사도 비교
- 장기 반복 약점 추적

---

## 브랜치 관계도

```
main (v1.x)
  └── feature/v2.0-stabilization → main (v2.0 태그)
        └── feature/replay-foundation
              └── feature/ict-detector-engine
                    └── feature/replay-coach
                          └── (main 머지 후) feature/aplus-setup-memory
```

---

## 브랜치 관리 원칙

1. 각 버전 브랜치는 이전 버전이 `main`에 머지된 후 생성
2. 실험적 작업은 `feature/` 브랜치에서만
3. `main`은 항상 배포 가능한 안정 버전 유지
4. 각 브랜치 완료 시 회귀 테스트 체크리스트 전체 통과 후 머지
