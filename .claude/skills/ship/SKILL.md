---
name: ship
description: "리뷰·커밋이 끝난 작업을 agent/<이슈번호>-<요약> 브랜치로 push하고 draft PR을 만든다. 본문은 .github/pull_request_template.md의 6개 항목. 머지는 하지 않는다 (사람 몫)."
when_to_use: "'PR 올려줘', '올려줘', 'draft PR 만들어줘', 'ship', '푸시해줘', 이슈 작업이 끝나 사람에게 넘길 때. 예: '이슈 12 끝났으면 PR 올려줘'"
argument-hint: "[이슈번호]"
---

# Ship

이슈: $ARGUMENTS (없으면 브랜치 이름의 번호, 그것도 없으면 0 = 이슈 없음)
`gh`가 PATH에 없으면 `C:\Program Files\GitHub CLI\gh.exe` (Windows)

## 순서
1. **브랜치** — 현재 브랜치가 `agent/`로 시작하지 않으면 `git switch -c agent/<이슈번호>-<영문-요약>`
2. **커밋** — 커밋 안 된 변경이 있으면 `commit` 스킬 먼저 (리뷰 필수는 guard가 강제)
3. **검사를 새로 실행** — `python -m pytest` · `python -m ruff check .` · `python -m ruff format --check .` · `python -m mypy <src·tests·.claude/hooks 중 있는 것>`
   - 하나라도 실패하면 멈추고 보고한다. 실패한 상태로 PR을 올리지 않는다
   - 결과 줄(예: `136 passed`)을 그대로 본문에 쓴다
4. **본문** — `.github/pull_request_template.md`를 채워 `.claude/tmp/pr-body.md`에 Write 도구로 쓴다
   - 변경 이유: `Closes #<번호>` (0이면 "이슈 없음" + 배경)
   - 핵심 변경: `git log main..HEAD --oneline`과 `git diff main...HEAD --stat` 기준
   - 리뷰 지적: `.claude/state/gate-log.jsonl`의 `review-rejected`/`review-approved` 기록을 **Read 도구로** 읽어
     (셸로 읽으면 guard가 막는다) 이 브랜치 기간의 라운드별 🔴/🟡 → 어떻게 반영했는지(또는 안 한 이유)
   - 확인하지 못한 부분·위험 지점은 솔직하게. 비워 두지 말고 없으면 "없음"과 근거
   - 본문에 시크릿·토큰·환경변수 값을 쓰지 않는다. 리뷰 지적은 원문(코드 인용)을 붙이지 말고 요약한다
5. **push** — `git push -u origin <브랜치>` (agent/* 외 브랜치·force push는 guard가 차단)
6. **PR** — 이 브랜치 PR이 있으면(`gh pr view --json url`) `gh pr edit --body-file .claude/tmp/pr-body.md`,
   없으면 `gh pr create --draft --base main --title "<type: 요약>" --body-file .claude/tmp/pr-body.md`
7. PR URL과 "머지는 사람이 검토 후 진행"을 보고한다

## 하지 않는 것
- `gh pr merge`, `gh pr ready`, 자동 머지 — 머지와 ready 전환은 사람이 한다 (guard가 차단)
- draft 없는 PR — guard가 차단
- main 직접 push, force push — guard와 GitHub Ruleset이 차단
