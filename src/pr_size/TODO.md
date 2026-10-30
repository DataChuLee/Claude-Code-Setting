# pr_size TODO
> 이슈: #5 · SPEC: ./SPEC.md

## NOW
- [ ] 리뷰 후 커밋·PR

## DONE
- 테스트 작성(tests/test_pr_size.py) · 구현(counter.py, __main__.py) · pytest/ruff/mypy 통과

## BLOCKER
- (없음)

## 리뷰 기록
- 2026-10-30 reviewer ✅ 승인 (🔴 없음)
  - 🟡 CLI 페이지 배열 입력 테스트, `.claude/` 접두사 경계(`src/.claude/x.md`, `.claudex/a.md`) 테스트 없음 — 미반영
  - 💡 RecursionError 미처리, 음수 허용, `_counts` 이름/docstring — 미반영
