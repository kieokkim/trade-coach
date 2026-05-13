
## TradeCoach v2.0 작업 규칙

### 공통 조건 (모든 작업에 적용)
- 작업 브랜치: feature/v2.0-stabilization
- 기준 파일: graph.py + nodes/*.py (모든 코드 작업)
- 수정 금지: final_notebook.ipynb
- 기존 파일 최소 수정 원칙 (요청된 것만 변경)
- 노드 파일에 logger 적용 필수
- 작업 완료 후 git add -A && git commit

### 커밋 컨벤션
- feat: 새 기능
- fix: 버그 수정
- refactor: 기능 변경 없는 개선
- docs: 문서 수정
