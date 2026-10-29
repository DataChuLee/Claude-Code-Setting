---
name: commit
description: "ruff 린트·포맷과 pytest를 통과시킨 뒤 로컬에 커밋한다. push는 하지 않는다 (push와 PR은 ship 스킬 담당)."
when_to_use: "'커밋해줘', '저장해줘', '변경사항 커밋', 작업 단위가 끝나 기록할 때. 예: '여기까지 커밋해줘'"
argument-hint: "[커밋 메시지]"
---

# Commit

메시지: $ARGUMENTS (없으면 변경 내용을 보고 생성)

## 순서
1. `ruff check --fix .` → `ruff format .`
2. `python -m pytest` — 실패하면 **중단하고 보고** (커밋하지 않음)
3. 변경 파일을 스테이징 (`git add <파일>` — `.env` 등 시크릿은 훅이 차단)
4. `git commit -m "<메시지>"`

## 메시지 규칙
`feat|fix|refactor|test|docs|chore: 설명` — 예: `feat: 문서 검색 API 추가`

## 하지 않는 것
- `git push` — main 직접 push 금지. push와 draft PR은 `ship` 스킬(Phase 3)이 담당
- `--no-verify` — 훅이 차단함
