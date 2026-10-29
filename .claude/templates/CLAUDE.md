# {프로젝트명}
{이 프로젝트가 무엇을 해결하는지 1-2문장}

## 스택
Python 3.11+ · {FastAPI} · pytest · ruff

## 명령
- 테스트: `python -m pytest`
- 린트/포맷: `ruff check --fix . && ruff format .`

## 구조
- 기능 코드: `src/<기능>/` — 각 폴더에 `SPEC.md`(요구사항) · `CLAUDE.md`(지도) · `TODO.md`(작업)
- 테스트: `tests/test_<기능>.py`

## 규칙
- 브랜치 `agent/<이슈번호>-<요약>`, 커밋 `feat|fix|refactor|test|docs|chore: 설명`
- API 응답 `{data, error, meta}`, 에러는 `AppException`
- 하네스 규칙(작업 흐름·금지 사항)은 `.claude/CLAUDE.md`에 있다
