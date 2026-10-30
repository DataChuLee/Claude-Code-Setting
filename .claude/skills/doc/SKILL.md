---
name: doc
description: "완성된 기능에 docstring, README 섹션, API 엔드포인트 문서를 reviewer 에이전트로 작성한다."
when_to_use: "'문서화해줘', 'docstring 달아줘', 'README 써줘', 'API 문서', 기능 구현과 리뷰가 끝난 뒤. 예: '검색 API 문서 만들어줘'"
argument-hint: "[파일 또는 기능명]"
---

# Doc

대상: $ARGUMENTS (없으면 마지막으로 완성된 기능)

## 순서
1. 대상을 **`reviewer` 에이전트**에 넘긴다
2. 작성: 함수·클래스 docstring, README 섹션(기능 설명 + 사용 예시), API 엔드포인트 문서(FastAPI일 때)
3. 작성한 문서 목록을 출력
