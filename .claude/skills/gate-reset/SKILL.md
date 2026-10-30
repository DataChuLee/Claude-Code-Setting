---
name: gate-reset
description: "검증 게이트가 재시도 2회를 넘겨 멈췄을 때, 사람이 확인한 뒤 재시도 횟수를 초기화한다. 사람만 실행 (Claude는 호출 불가)."
disable-model-invocation: true
---

# Gate Reset

사람이 `/gate-reset`을 직접 입력해 재시도 횟수가 초기화됐다 (UserPromptExpansion 훅이 처리. 사람이 입력할 때만 발생).

1. `.claude/state/gate-log.jsonl`의 마지막 실패 기록을 읽고, 무엇이 왜 실패했는지 3줄로 요약한다
2. 같은 방법을 반복하지 말고, 다른 접근을 제안한 뒤 사람의 지시를 기다린다
