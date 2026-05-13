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
