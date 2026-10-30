---
name: commit
description: "검사를 통과한 변경을 로컬에 커밋한다. 커밋 전 reviewer 리뷰가 필수(훅이 강제). push는 하지 않는다 (push와 PR은 ship 스킬 담당)."
when_to_use: "'커밋해줘', '저장해줘', '변경사항 커밋', 작업 단위가 끝나 기록할 때. 예: '여기까지 커밋해줘'"
argument-hint: "[커밋 메시지]"
---

# Commit

메시지: $ARGUMENTS (없으면 변경 내용을 보고 생성)

## 순서
1. **검사만 한다 (파일을 고치지 않음)** — `python -m ruff check .` · `python -m ruff format --check .` · `python -m pytest`
   - 실패하면 중단하고 보고. 고친 뒤에는 코드가 바뀌었으니 리뷰부터 다시
   - 여기서 `--fix`/`format`으로 고치면 리뷰한 코드와 달라져 커밋이 차단된다
2. 리뷰 기록이 없거나 리뷰 후 코드가 바뀌었으면 `review` 스킬 먼저 (안 하면 guard가 커밋을 막음)
3. 변경 파일 스테이징 (`git add <파일>` — `.env` 등 시크릿은 훅이 차단)
4. `git commit -m "<메시지>"`

## 메시지 규칙
`feat|fix|refactor|test|docs|chore: 설명` — 예: `feat: 문서 검색 API 추가`

## 하지 않는 것
- `git push` — push와 draft PR은 `ship` 스킬이 담당
- `--no-verify` — 훅이 차단함
