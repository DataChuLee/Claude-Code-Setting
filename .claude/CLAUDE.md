# 하네스 지도
AI-Native 개발 하네스. 전체 계획 @docs/PLAN.md · 설계 기록 docs/HARNESS.md
(프로젝트별 내용은 루트 `CLAUDE.md`, 기능별 내용은 `src/<기능>/CLAUDE.md`)

## 작업 흐름 — 프로젝트 스킬을 우선 사용 (전역 superpowers 등보다 먼저)
의도(자연어·이슈) → `tdd`(SPEC 승인 → Red → Green → Refactor) → `review` → `doc` → `commit`
- 사람 승인 지점: SPEC 승인, PR 머지. 그 외 단계는 스킬이 진행
- 기능 문서: `src/<기능>/SPEC.md` · `CLAUDE.md` · `TODO.md` (템플릿 `.claude/templates/`)

## 명령
- 테스트 `python -m pytest` · 린트 `ruff check --fix . && ruff format .`
- 하네스 자체 테스트 `python -m pytest .claude/hooks/test_guard.py`

## 금지 (훅 `.claude/hooks/guard.py` 와 settings.json deny 가 강제)
- 시크릿(.env, 키 파일, 토큰, KEY/TOKEN 환경변수) 읽기·쓰기·출력
- main/master 직접 push, force push, `--no-verify`
- `gh pr merge`(머지는 사람), 저장소 설정·브랜치 보호·Secrets 변경
- 차단되면 우회하지 말고 사용자에게 알린다

## Phase
PLAN.md 규칙: 한 번에 Phase 하나, 사용자 승인 없이 다음 Phase로 넘어가지 않는다
