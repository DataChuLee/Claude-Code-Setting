# 하네스 지도
AI-Native 개발 하네스. 전체 계획 @../docs/PLAN.md · 설계 기록 docs/HARNESS.md
(프로젝트별 내용은 루트 `CLAUDE.md`, 기능별 내용은 `src/<기능>/CLAUDE.md`)

## 작업 흐름 — 프로젝트 스킬을 우선 사용 (전역 superpowers 등보다 먼저)
의도(자연어·이슈) → `spec`(사람 승인) → `tdd` (+LLM 기능은 `eval`) → `review` → `commit` → `ship`(draft PR)
- 사람 승인 지점: SPEC 승인, PR 머지, 게이트 에스컬레이션(`/gate-reset`)
- 기능 문서: `src/<기능>/SPEC.md` · `CLAUDE.md` · `TODO.md` (템플릿 `.claude/templates/`)

## 명령
- 테스트 `python -m pytest` (`.claude/hooks` 포함, eval 제외) · 평가 `python -m pytest -m eval`
- 린트 `python -m ruff check . && python -m ruff format .` · 타입 `python -m mypy src .claude/hooks`

## 게이트 (훅이 강제)
- 응답 종료 시: pytest·ruff·mypy·TODO 갱신 검사, 실패하면 최대 2회 재시도 후 멈춤
- 커밋 시: reviewer가 본 코드와 지금 코드가 같아야 함
- 상태·로그: `.claude/state/` (gate.json, review.json, gate-log.jsonl)

## 금지 (`.claude/hooks/guard.py` · settings.json deny)
- 시크릿(.env, 키 파일, 토큰, KEY/TOKEN 환경변수) 읽기·쓰기·출력
- `agent/*` 외 브랜치 push(main 포함), force push, `--no-verify`, draft 아닌 PR
- `gh pr merge`(머지는 사람), 저장소 설정·브랜치 보호·Secrets 변경
- 차단되면 우회하지 말고 사용자에게 알린다
- guard.py는 **한 번에 완결된 수정**으로만 고친다 (중간 상태로 깨지면 모든 도구가 막힘)

## Phase
PLAN.md 규칙: 한 번에 Phase 하나, 사용자 승인 없이 다음 Phase로 넘어가지 않는다
