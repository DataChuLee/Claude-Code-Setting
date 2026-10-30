# PR 크기 계산 (pr_size) SPEC
> 상태: 승인됨 (agent:build, 이슈 #5)
> 이슈: #5

## 왜 (문제)
`.github/workflows/ci.yml`의 "PR 크기" 단계는 jq 한 줄에 규칙(사람용 문서 제외)이 들어 있어 테스트가 없다. 규칙을 Python 함수로 옮기고 테스트로 고정한다.

## 무엇을 (요구사항)
- `src/pr_size/` 아래 새 모듈이 `pulls/{n}/files` 응답의 파일 목록을 받아 크기 제한에 셀 줄 수(`additions + deletions` 합)를 돌려준다.
- 센다/안 센다 규칙 (현재 ci.yml jq와 동일하게 유지):
  - `.md`로 끝나는 파일은 세지 않는다.
  - 예외: 경로가 `.claude/`로 시작하는 `.md`, 또는 파일 이름이 `CLAUDE.md`인 `.md`는 센다.
  - `.md`가 아닌 파일은 항상 센다.
- 명령줄: JSON 파일 경로를 받아 숫자 하나를 stdout에 출력한다. 파일은 항목 배열(한 페이지) 또는 페이지 배열의 배열(`gh api --paginate | jq -s` 결과)을 모두 허용한다.
- 표준 라이브러리만 사용한다. 파일 구성: `src/pr_size/` (모듈 + `SPEC.md`·`CLAUDE.md`·`TODO.md`), `tests/test_pr_size.py`.

## 인수조건 (테스트로 옮겨질 문장)
- [x] `.py` 파일(additions 3, deletions 2)만 있을 때 결과는 5다.
- [x] `README.md`(additions 10, deletions 0)만 있을 때 결과는 0이다.
- [x] `docs/PLAN.md`, `src/x/SPEC.md`처럼 `.claude/` 밖이고 이름이 `CLAUDE.md`가 아닌 md는 세지 않는다.
- [x] `.claude/agents/reviewer.md`, `.claude/skills/spec/SKILL.md`처럼 `.claude/` 아래 md는 센다.
- [x] 루트 `CLAUDE.md`와 `src/x/CLAUDE.md`는 센다.
- [x] `.claude/` 아래의 `.md`가 아닌 파일(예: `.claude/hooks/guard.py`)은 센다.
- [x] `docs/NOTCLAUDE.md`처럼 이름만 `CLAUDE.md`로 끝나는 파일은 세지 않는다 (결정 1).
- [x] 목록이 비어 있을 때(`[]`) 결과는 0이다.
- [x] 센 파일과 안 센 파일이 섞여 있을 때 센 파일의 `additions + deletions`만 합산한다.
- [x] 입력이 페이지 배열의 배열(`[[...], [...]]`)이면 모든 페이지를 합산한다. 빈 페이지가 섞여도 된다.
- [x] 명령줄에 JSON 파일을 주면 stdout에 숫자와 줄바꿈만 출력하고 종료 코드 0이다.
- [x] 파일이 없거나 JSON이 아니거나 배열 형태가 아니면 종료 코드가 0이 아니고 stderr에 이유를 출력한다 (stdout에는 숫자를 내지 않는다).
- [x] 항목에 `filename`/`additions`/`deletions`가 없거나 정수가 아니면 오류로 처리한다 (조용히 0으로 세지 않는다).

## 범위 밖
- `.github/workflows/ci.yml`에 연결하는 것 (워크플로 파일은 사람이 바꾼다)
- `.claude/` 아래 파일 수정
- GitHub API 호출, 크기 상한 비교와 통과/실패 판정 (이 모듈은 숫자만 낸다)
- 외부 의존성 추가

## 결정 (소유자 승인: 제안 4개 모두 수락)
1. **이름이 정확히 `CLAUDE.md`인 파일만** 센다. `docs/NOTCLAUDE.md`는 세지 않는다 (ci.yml jq의 접미사 일치와 다름 — 연결할 때 맞춘다)
2. 확장자는 대소문자를 구분한다. `.md`만 md로 본다 (`.MD`는 md가 아니므로 센다)
3. rename된 파일은 새 `filename`만 보고 판정한다. `previous_filename`은 무시한다
4. 명령줄 진입은 `python -m pr_size <파일>`이다
