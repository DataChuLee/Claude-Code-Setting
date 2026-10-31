# HARNESS.md — 설계 결정 · 실패 · 해결 기록
PLAN.md 진행 규칙 4에 따라 Phase마다 누적한다.

---

## 0. 출발 전 결정 (2026-10-30)
| 결정 | 이유 |
|---|---|
| 뼈대 = 공통(SDD+TDD) + LLM 확장(Eval) | LLM 서비스도 결정적 코드(청킹·API)는 TDD 대상. 하네스 두 벌은 드리프트 |
| 연습 프로젝트 = 별도 저장소의 RAG Q&A API, LLM은 OpenAI | 템플릿과 프로젝트 기록 분리. 두 유형(TDD·Eval)을 모두 검증 가능 |
| Actions 에이전트 = Claude Code 먼저, Codex는 나중에 비교 | Codex는 `.claude/` 설정(훅·deny)을 읽지 않아 안전장치가 루프에서 빠짐 |
| 트리거 = 자연어 (스킬), 강제 = 훅, 사람 = 승인 지점(SPEC·머지) | 사람을 "명령 입력자"가 아니라 "의사결정자" 자리에 둔다 |

## 이전 시도 회고 — sample-automation (2026-03-30, 삭제 전 기록)
- TODO의 "훅 동작 확인", "/commit 파이프라인 테스트"가 끝내 미체크 → 원인: settings.json 훅이 존재하지 않는 `$HOME/.claude/hooks/`를 가리켜 **한 번도 실행되지 않았음**. 또 `$CLAUDE_FILE_PATH`는 존재하지 않는 변수(입력은 stdin JSON)
- 코드는 커밋됐는데 TODO NOW는 미체크 → **말로만 지시한 단계는 지켜지지 않는다**. → Phase 2에서 Stop 훅으로 강제
- pytest/ruff가 의존성에 미선언, 타입체크 없음 → Phase 2 게이트에서 보완
- 가져온 것: `python -m pytest` 규칙, ruff 설정, `.gitignore`의 `.env`, 테스트 이름 규칙 `test_<동작>_<조건>_<결과>`

---

## Phase 1 — 하네스 기본층

### 설계
| 결정 | 이유 |
|---|---|
| 3겹 방어: deny 규칙 → PreToolUse 훅 → GitHub 브랜치 보호 | 공식 문서: deny 규칙은 보안 경계가 아님 (`git -C . push`처럼 변형하면 못 막음). 서버 측 보호가 최종 경계 |
| 훅은 Python (`guard.py`) | Phase 4 CI 러너는 Linux → PowerShell 훅은 못 돎 |
| matcher `Bash\|PowerShell\|Read\|Edit\|Write\|NotebookEdit\|Grep` | Windows에선 PowerShell 도구가 기본 셸. Bash만 막으면 구멍 |
| `onFailure: "block"` (fail closed) | 검사기가 고장 나면 통과가 아니라 차단 |
| 하네스 지도는 `.claude/CLAUDE.md`, 루트 `CLAUDE.md`는 프로젝트용 | 둘 다 로드됨(공식 문서). clone 후 프로젝트 지도와 충돌하지 않음 |
| 커맨드 → 스킬 전환, `init`→`scaffold`, `tdd-cycle`은 `tdd`에 병합 | 자연어 자동 실행. 내장 `/init`과 이름 충돌 회피 |
| 기능 문서 `src/<기능>/{SPEC,CLAUDE,TODO}.md` | Kiro의 requirements/design/tasks 대응. 하위 CLAUDE.md는 그 폴더 작업 시 자동 로드 |
| 기존 ps1 훅 2개는 등록만 해제 | Phase 2 검증 게이트에서 Python으로 다시 만듦 |

### 실패와 해결
1. **한글이 깨진 차단 메시지** — 첫 실전 시도에서 `[harness-guard] ȯ�溯��...`. 원인: Windows Python 기본 입출력이 cp949인데 Claude Code는 UTF-8. 출력 JSON이 깨지면 이유가 전달되지 않고(차단은 `onFailure`로 유지), 입력 쪽에선 한글 명령을 잘못 읽을 수 있음.
   - 단위 테스트가 놓친 이유: 테스트도 cp949로 주고받아 양쪽이 같이 틀렸음
   - 해결: 테스트를 UTF-8 입출력으로 바꿔 **먼저 실패 재현**(4개 실패) → `guard.py`에서 stdin/stdout/stderr를 UTF-8로 재설정 → 통과
   - 교훈: 테스트 환경은 실제 호출자(Claude Code)의 조건을 흉내 내야 한다
2. 커밋 메시지 속 `.env` 글자도 차단되는 오탐 → `git commit` 세그먼트는 경로 검사 제외 (테스트 추가 후 수정)
3. **인터프리터 우회** — `python -c "open('.env')"`처럼 따옴표 속 경로는 토큰 검사로 못 잡음. 원문에서 경로 후보를 정규식으로 찾아 검사하도록 변경 (테스트 3개 실패 확인 → 수정). 같은 과정에서 `.env.example.bak` 오탐도 발견해 수정
   - 부작용: `.env` 글자가 들어간 셸 명령(예: `grep "\.env"`)도 막힘. 파일 도구(Read/Grep)는 경로만 검사하므로 그쪽을 쓴다
   - 한계: 문자열 검사라 난독화(base64 등)는 못 막는다 → 최종 경계는 GitHub 브랜치 보호, 시크릿은 애초에 저장소 밖(GitHub Secrets)에 둔다
4. **재리뷰에서 발견: 실행 파일 경로·접두어 우회** — 첫 단어가 정확히 `git`/`gh`일 때만 검사해서 `git.exe push origin main`, `"C:\...\gh.exe" pr merge`, `env FOO=1 git push`, `& git ...`, `sudo git ...`가 통과. 이 세션에서 gh를 전체 경로로 써 왔으니 실제로 일어날 수 있던 일
   - 해결: 토큰의 파일 이름(확장자 제외)으로 git/gh를 찾음 (테스트 5개 실패 확인 → 수정). 실전에서 전체 경로 `gh.exe pr merge 99999`가 막히는 것 확인
5. **오탐: `git stash push`를 main push로 판정** — `push`가 명령 어디에든 있으면 push로 봤음 → git 전역 옵션(`-C` 등)을 건너뛴 **하위 명령**이 push일 때만 검사
6. **`.claude/CLAUDE.md`의 `@docs/PLAN.md` 경로 오류** — import는 그 파일 기준 상대 경로(공식 문서) → `@../docs/PLAN.md`
7. builder 에이전트가 옛 구조(레이어별 폴더, 루트 TODO.md)를 안내 → `src/<기능>/{SPEC,CLAUDE,TODO}.md`, SPEC 인수조건 ↔ 테스트 1:1로 수정

### 검증 결과
**단위 테스트**: `python -m pytest .claude/hooks/test_guard.py -W error` → **75 passed**

**실전 시도 (이 세션, 2026-10-30)** — push는 존재하지 않는 remote 대상으로 시도해 안전 확보
| 시도 | 결과 | 막은 층 |
|---|---|---|
| `cat .env` (Bash) | 차단: 환경변수 파일(.env)은… | 훅 |
| `Get-Content .env` (PowerShell) | 차단 | 훅 |
| Read 도구로 `.env` | 차단: denied by your permission settings | deny 규칙 |
| `git -C . push nonexistent main` | 차단: main 직접 push 는 금지… | 훅 (deny 규칙이 못 잡는 변형) |
| `git push nonexistent HEAD` (현재 main) | 차단 | 훅 (현재 브랜치 검사) |
| `git push origin main` | 차단 | 훅 (훅이 deny 규칙보다 먼저 실행됨) |
| `git push --force nonexistent agent/0-test` | 차단 | 전역 command-guard가 먼저. 하네스 차단은 단위 테스트로 증명 |
| `gh pr merge 1` / `gh auth token` / `gh secret list` | 차단 | 훅 |
| `echo $env:OPENAI_API_KEY` | 차단 | 훅 |
| `git status` | 허용 | — |
| `git push --dry-run origin agent/0-test` | 허용 (브랜치가 없어 git이 거절, 원격 변화 없음) | — |

| `python -c "print(open('.env').read())"` | 차단 | 훅 (우회 수정 후) |

**알게 된 점**: Bash에서는 PreToolUse 훅이 deny 규칙보다 먼저 판정해서 deny 층을 따로 관찰할 수 없었다. Read 도구에서는 deny 규칙이 먼저 막았다.

**deny 층 단독 검증** — 하네스를 임시 폴더에 복사하고 hooks만 뺀 뒤 `claude -p`로 `gh secret list` 실행 요청, `--allowedTools "Bash(gh *)"`로 허용 규칙까지 줌
→ `Permission to use Bash with command gh secret list has been denied.` (deny가 allow보다 우선). Claude는 CLAUDE.md에 따라 우회를 시도하지 않음

**자연어 트리거 검증** — 임시 복사본에서 `claude -p "덧셈 함수 테스트 먼저 만들어줘" --permission-mode plan`
→ `Skill: tdd` 호출 (전역 superpowers의 test-driven-development가 아니라 **프로젝트 스킬**이 선택됨). 이어서 SPEC 템플릿을 읽는 1단계까지 진행
- 1회 시도라 확률적 동작의 일부만 본 것. 빗나가는 사례는 Phase 5 LEARNING.md에 누적

### 운영 메모
- **훅이 모든 셸 명령을 막을 때** (python을 못 찾는 등): `onFailure: "block"` 때문. 터미널에서 `python --version` 확인 → 안 되면 `.claude/settings.json`의 `"command": "python"`을 python 전체 경로로 바꾼다
- **GitHub 브랜치 보호 (사용자가 직접 설정)**: 저장소 → Settings → Branches(또는 Rules → Rulesets) → `main` 대상 규칙 추가 → *Require a pull request before merging*, *Block force pushes* 체크
  - 2026-10-30 적용: 사용자가 웹에서 Ruleset `main` 생성 (Active, Bypass 없음 → 관리자도 적용, 대상 default branch, 필요 승인 0 — 1인 저장소라 1이면 본인 PR 머지 불가). 에이전트가 대신 설정하지 않음 — PLAN 금지 사항이자 guard가 막는 동작이고, 에이전트가 걸 수 있는 보호는 에이전트가 풀 수도 있어서
  - 확인(읽기 전용): `gh api repos/<owner>/<repo>/rules/branches/main` → `deletion`, `non_fast_forward`, `pull_request(required_approving_review_count: 0)` 3개. 이 API는 Active 규칙만 돌려준다
  - status check 필수화는 Phase 4에서 CI를 만든 뒤 추가
- 전역 `~/.claude/mods/command-guard`는 이 PC에만 있다. clone·CI에선 하네스 `guard.py`만 동작

- 기존 `post-write.ps1`·`on-stop.ps1` 삭제 (등록 해제 상태였고, Phase 2에서 Python 게이트로 대체)

---

## Phase 2 — 검증 게이트

### 설계
| 결정 | 이유 |
|---|---|
| **재시도 카운터 = 파일** (`.claude/state/gate.json`, 세션별). Stop 훅이 실패마다 +1, 2회까지 `decision:"block"`(되돌려 보냄), 3번째에 `continue:false`(멈춤) | PLAN: "말이 아니라 카운터 파일이나 훅으로 강제". 모델이 뭐라고 하든 횟수는 파일이 센다 |
| 카운터 초기화 = 사람이 `/gate-reset` 입력 (`UserPromptExpansion` 훅 + `disable-model-invocation`) | UserPromptSubmit은 Claude Code가 스스로 시작한 턴에도 발생(공식 문서) → 사람 입력을 구별 못 함. UserPromptExpansion은 사용자가 직접 입력한 명령에만 발생 |
| 검사: pytest · ruff check · ruff format --check · mypy · 기능 TODO.md 갱신 | TODO 강제는 Phase 1 회고(말로만 지시하면 방치)의 환류 |
| 통과 해시가 같으면 재검사 생략 | 커밋 전 변경이 남아 있는 동안 매 턴 같은 검사를 반복하지 않게 |
| PostToolUse(Edit\|Write)는 ruff만, exit 2 → Claude에게 즉시 | pytest는 TDD Red에서 일부러 실패하므로 저장마다 돌리면 소음 |
| **리뷰는 커밋 시점에 강제** (guard가 `git commit` 전 해시 대조) | Stop에 두면 작업 중 질문하려고 멈출 때마다 리뷰를 강요 |
| 리뷰 해시 = 마지막 커밋 대비 바뀐 .py 경로+내용 | 스테이징 여부와 무관해야 commit 스킬의 `git add`가 리뷰를 무효로 만들지 않음 |
| commit 스킬은 **검사만** (ruff --fix/format 안 함) | 커밋 직전 자동 수정이 리뷰한 코드를 바꿔 커밋이 영원히 막히는 함정 |
| reviewer 에이전트 `tools: Read, Grep, Glob, Bash` | 수정 권한이 없어야 구현과 분리됨 |
| eval 마커는 기본 게이트에서 제외 (`addopts = -m 'not eval'`) | LLM 평가는 API 비용 → eval 스킬이 명시적으로 실행 |
| 도구는 전부 `python -m ...`, 루트 `pyproject.toml`에 dev 의존성 | PATH 차이 제거. ruff가 실행 파일로만 깔려 `python -m ruff`가 안 되던 문제 발견 → pip 설치 |

### 실패와 해결
1. **guard 자기 잠김 (2회)** — guard.py를 두 단계로 고치다 중간 상태(정의 전 호출, import 누락)에서 guard가 죽음 → `onFailure:"block"` 때문에 Bash·Edit·Write 등 **모든 도구가 막혀 guard를 고칠 수도 없음**
   - 임시 복구: matcher 목록에 없던 `Monitor` 도구로 한 줄 수정 (사용자 승인). → 이것 자체가 **구멍**
   - 해결 ①: matcher `*` + guard가 도구 이름이 아니라 **입력 형태**(command / 경로)로 판정 → Monitor 등 셸 실행 도구 전부 검사 (실전: Monitor로 `gh pr merge` 차단 확인)
   - 해결 ②: **`run_guard.py` 진입점** — guard가 고장 나면(예외·문법 오류 포함) guard.py 수정만 허용, 나머지 차단. 이후 같은 실수를 두 번 더 했을 때 이 길로 바로 복구됨
   - 교훈: fail closed 장치에는 **복구 경로**가 함께 있어야 한다. 검사기 자신을 고치는 수정은 한 번에 완결되게
2. **새 ruff가 한글을 2칸으로 세어 E501** → E501 끔 (줄 길이는 formatter 담당, code-quality 스킬 기준과 일치)
3. **커밋 리뷰 검사가 엉뚱한 저장소를 봄** — 세션 저장소 기준이라 `git -C <다른곳> commit`, `cd 다른곳 && git commit`도 막음 → `cd`·`-C`를 따라가 실제 커밋 대상을 검사. Git Bash 경로(`/c/..`)를 Windows 경로로 변환
4. **셸 문자열 오탐** — heredoc 속 `git commit`·`.env` 글자를 명령으로 판정 → 코드·문서 작성은 파일 도구(Edit/Write, 경로만 검사)로
5. **게이트 테스트 77초** — 매 테스트가 실제 pytest/ruff/mypy 실행 → 카운터 로직 테스트는 검사 결과를 가짜로 바꿔 끼우고, 실제 도구는 대표 테스트 2개만 → 전체 약 35초 (Windows git init 비용이 큼)
6. **reviewer가 찾은 하네스 구멍** (검증용 임시 저장소에서) — mypy가 `src/`·`.claude/hooks/`만 검사해 루트 .py·`tests/`는 타입 검사 밖, pytest `pythonpath` 미설정 → `tests/`와 그 밖에서 바뀐 .py까지 mypy 대상, `pythonpath = ["src", "."]`

7. **커밋 전 reviewer 리뷰에서 🔴 3건 (❌ 수정 후 재검토)** — 리뷰어가 `guard.decide`를 직접 돌려 재현까지 함
   - 🔴 모델이 직접 우회: `.claude/state/review.json` 쓰기, `python gate.py review-done`(리뷰 위조), `gate.py reset`(사람 전용 초기화) → 상태 폴더 쓰기·두 모드 직접 실행 차단 (읽기는 Read 도구로 허용)
   - 🔴 커밋 감지 우회: `bash -c "git commit"`(따옴표 한 토큰), `git -c alias.ci=commit ci`, `git merge`(커밋 생성) → `-c`/`-Command` 안의 명령을 재귀 검사, `git -c alias.*` 차단, merge·cherry-pick·revert·am·pull·rebase도 리뷰 대상
   - 🔴 멈춘 테스트가 게이트를 조용히 통과: 검사당 240초 × 4 > 훅 timeout 300초 → 훅이 죽으면 카운터도 안 오르고 로그도 없음 → 모든 검사 합계 270초 마감, 초과는 실패로 셈
   - 🟡 반영: `/gate-reset` 경로를 실제 `main()`으로 테스트, 🔴 남은 리뷰는 커밋을 안 열어 줌, `.claude/**`·`pyproject.toml` 변경도 리뷰 대상(게이트를 끌 수 있는 파일), ruff stderr 전달, 깨진 gate.json 대비, 해시 구분자
8. **리뷰 보고서가 비어 있음** — 위 🔴 남은 리뷰 차단을 넣고 보니 `review.json`의 summary가 빈 문자열. 공식 문서: 최신 버전은 서브에이전트 보고서를 `SubagentHandback` 도구로 넘기고 SubagentStop의 `last_assistant_message`는 맺음말뿐 → PostToolUse(`SubagentHandback`)에서 `tool_input.message`로 기록, 빈 보고서·reviewer 아닌 에이전트는 무시
9. guard 수정을 **"정의 먼저, 연결은 나중"** 순서로 하자 이번엔 잠기지 않음 (정의만 추가하는 수정은 언제 멈춰도 안전)
10. **2차 reviewer 리뷰에서 🔴 4건 (또 ❌)** — 리뷰 기록 장치 자체의 구멍
   - 🔴 거절이 승인으로 바뀜: Handback이 ❌를 기록한 뒤 SubagentStop이 ❌ 없는 맺음말로 덮어씀 → SubagentStop 등록 제거, Handback만
   - 🔴 `"❌" in 보고서` 판정은 이모지 없는 "수정 후 재검토"를 승인으로 봄 → `승인 가능 여부:` 줄을 찾아 판정, 줄이 없으면 거절
   - 🔴 상태 경로 우회: `.claude/hooks/../state`, `.CLAUDE/STATE`(NTFS 대소문자 무시) → resolve한 경로를 대소문자 무시로 검사
   - 🔴 커밋 감지 우회: `bash -lc`·`sh -ec`(붙여 쓴 플래그), `git config alias.ci commit`, `--config-env` → `-[a-z]*c` 전부 셸 플래그로, alias 정의·`--config-env` 차단
   - 🟡 `pull`·`rebase`는 리뷰 대상에서 제외 (차단 소음)
   - 교훈: 검증 장치를 만들면 **그 장치를 속이는 방법**이 다음 공격 면이 된다. 분리된 리뷰어가 두 번 연속 그 면을 찾아냄
   - 3차 리뷰 🔴 1건: `승인 불가`·`미승인`도 '승인' 글자를 포함해 승인으로 읽힘 → 정확히 `✅ 승인`으로 시작할 때만 승인
   - **리뷰 기록 훅 실전 확인**: 3차 리뷰(❌)가 SubagentHandback으로 오자 `review.json`에 `agent_type: reviewer`, `rejected: true`, `hash: null` 기록 → Handback 페이로드에 agent_type이 실린다는 것과 거절이 커밋을 열지 않는다는 것을 실제로 확인
11. 게이트 상태 파일이 리뷰 해시를 흔듦 — `.gitignore`가 없으면 `.claude/state/`가 "바뀐 설정"으로 잡혀 매번 해시가 달라짐 → 상태 폴더는 항상 리뷰 대상에서 제외

### 검증 결과 (일부러 실패시키기 — 임시 저장소에서 `claude -p`)
| 시나리오 | 결과 |
|---|---|
| 항상 실패하는 테스트 + "고치지 마라" 지시 | gate-log: `block 1/2` → `block 2/2` → `escalate 3` 후 멈춤. 모델이 매번 "고치지 않겠다"고 답해도 파일 카운터대로 정확히 3번째에 정지 |
| `import os` 한 줄 저장 | PostToolUse가 즉시 `F401 os imported but unused` 전달 → Claude가 고침 → Stop 게이트 pass |
| 리뷰 없이 `git add . && git commit` | `[harness-guard] 커밋 전에 reviewer 에이전트로...` 차단 → Claude가 review 스킬로 reviewer 호출 → SubagentStop이 해시 기록 → 커밋 성공 |
| 코드 변경 후 TODO.md 미갱신 | 단위 테스트로 검증 (`test_feature_code_without_todo_update_fails`) |
| 위험 명령 회귀 | Phase 1 테스트 전부 통과 + 실전 차단 확인 |
| 이 세션 자체 (dogfooding) | 저장할 때마다 PostToolUse가 실제 실수(정의 전 호출, import 누락)를 즉시 잡음. 이 커밋도 reviewer 리뷰 후에만 가능 |
| 리뷰 지적 우회 경로 (실전) | `bash -c "git push nonexistent main"` 차단, Write로 `.claude/state/review.json` 차단, `gate.py review-done` 직접 실행 차단, Read는 허용 |
| `/gate-reset` (사람이 직접 입력) | gate-log에 `result: reset` 기록, 재시도 횟수 0 → UserPromptExpansion 페이로드에 `command_name: "gate-reset"`이 실린다는 것을 실제로 확인 |
| 단위 테스트 | `python -m pytest` → 125 passed (`.claude/hooks` 포함) |

### 알려진 한계
- 문자열 검사: Python 스크립트 안에서 `subprocess`로 git을 부르면 guard가 못 본다 (임시 저장소 초기 커밋을 이렇게 만듦 — 테스트 준비 용도로만). 최종 경계는 GitHub 브랜치 보호
- Stop 게이트 비용: 바뀐 코드가 있으면 응답 종료마다 전체 테스트(~35초). 통과 해시로 반복은 줄임
- Stop 게이트 훅 자체가 죽으면 막지 않고 통과 (fail open) — 응답이 영원히 끝나지 않는 상황을 피하려는 선택. 검사 시간 초과는 270초 마감으로 실패 처리되므로, 남은 fail open은 gate.py 버그뿐
- **모델이 `.claude/hooks/*`·`settings.json`을 고쳐 게이트를 끌 수 있다** — 하네스 개발 자체가 그 파일을 고치는 일이라 막지 않음. 대신 그 변경은 리뷰 대상이라 reviewer 승인 없이는 커밋되지 않고, 머지는 사람만 함
- 리뷰 판정은 보고서의 `승인 가능 여부:` 줄로 판단 (reviewer 출력 형식에 의존. 줄이 없으면 거절이라 안전한 쪽)
- **임의 Python으로 위조 가능**: `python -c "import gate; gate.review_done(...)"`, 문자열을 조립한 경로로 상태 파일 쓰기 → 문자열 검사로는 못 막음. 최종 경계는 사람이 머지하는 PR (Phase 3)
- 이미 전역에 등록된 git alias(`~/.gitconfig`)로 `git ci` 하면 커밋 감지를 못 함 (새로 정의하는 것만 막음)
- 셸 리다이렉트로 상태 파일 쓰기는 글자 그대로만 검사: `echo x > .claude/hooks/../state/...`, `cd .claude && echo x > state/...`는 못 막음 (파일 도구 경로는 정규화해서 막음). 임의 Python 위조와 같은 부류
- `pull`·`rebase`는 리뷰 대상이 아님
- 중첩 저장소(`sample-automation/`처럼 자체 `.git`)에서는 리뷰 기록이 세션 저장소에 쓰여 그 저장소 커밋이 막힘 → 중첩 저장소는 두지 않는다 (삭제 예정)
- `cd` 추적은 `Set-Location -Path X`, `$VAR`, `~`를 해석하지 못함 (모르면 차단 쪽)

---

## Phase 3. PR 자동화 (ship 스킬) — 2026-10-30

### 만든 것
- `.claude/skills/ship/SKILL.md` — 브랜치 확인 → (commit) → 검사 재실행 → 본문 작성 → push → draft PR (있으면 본문 갱신)
- `.github/pull_request_template.md` — 6개 항목: 변경 이유(이슈) · 핵심 변경 · 테스트와 결과 · 확인 못 한 부분 · 위험 지점 · 리뷰 지적과 반영
- guard: push 대상은 `agent/*`만, `gh pr create`는 `--draft`/`-d` 필수
- gate: 리뷰가 끝날 때마다 `gate-log.jsonl`에 `review-approved|review-rejected` + 보고서 기록

### 설계
| 결정 | 이유 |
|---|---|
| push 허용을 "main 금지"에서 "`agent/*`만 허용"으로 좁힘 | 금지 목록은 새 브랜치 이름(release 등)을 놓친다. 허용 목록이 최소 권한. Phase 4 루프 토큰도 같은 범위 |
| draft를 훅으로 강제 | PLAN 원칙 "말이 아니라 훅". 스킬 문구만으로는 모델이 `--draft`를 빠뜨릴 수 있다 |
| `gh pr ready`도 차단 (계획에선 안 막기로 했다가 리뷰 후 변경) | "ready 전환은 사람이"를 말로만 두면 Phase 2에서 고친 것과 같은 부류의 구멍. 사람은 웹·자기 터미널에서 하면 됨 |
| 리뷰 이력은 기존 `_log()`에 한 줄 추가 | `review.json`은 마지막 리뷰만 남아 "거절 → 수정 → 승인" 과정을 PR에 쓸 근거가 없었음. 새 파일 대신 기존 로그 재사용, Phase 5 원재료 |
| 본문 임시 파일 `.claude/tmp/pr-body.md` (gitignore) | Write 도구로 쓰면 셸 heredoc 오탐(본문 속 `.env`·`git commit` 글자)이 없음. CI에서도 같은 경로 |
| 검사를 ship에서 다시 실행 | 본문의 "테스트 결과"는 실제 실행 결과 줄이어야 한다. 기억이나 Stop 게이트 통과 사실로 대신하지 않음 |
| 이슈 없음 = 번호 0 | 로컬 작업용. Phase 4에서는 항상 이슈 번호가 있음 |

### 검증
| 시도 | 결과 |
|---|---|
| 단위 테스트 (먼저 작성 → 7개 실패 확인 → 구현, 리뷰 지적분도 7개 실패 확인 → 수정) | `python -m pytest` → 153 passed |
| 실전: `git push origin feature-x` | 차단 "push 는 agent/<이슈번호>-<요약> 브랜치에만" |
| 실전: draft 없이 `gh.exe pr create` (전체 경로) | 차단 "PR 은 draft 로만" |
| 실전: `git push origin HEAD:main` | 차단 "main 직접 push 는 금지" |
| **실전 ship → PR #1** | `git push -u origin agent/0-phase1-harness 2>&1` 통과(오탐 수정 후) → `gh pr create --draft` → https://github.com/DataChuLee/Claude-Code-Setting/pull/1 · 조회 결과 `isDraft: true`, base `main`, 커밋 9개, 본문 6개 섹션 모두 존재. 머지는 사용자 |

### 겪은 실패와 해결
1. **리뷰 1차 🔴: `git push --all origin`·`--mirror`가 통과** — refspec이 없으면 대상을 현재 브랜치(agent/…)로만 봤는데, 실제로는 main 포함 모든 브랜치를 올림(`--mirror`는 강제 갱신·삭제까지). `--all`/`--mirror`/`--branches` 차단
2. **리뷰 1차 🔴: `gh pr new`가 통과** — `new`는 `create`의 공식 별칭. 둘 다 검사
3. 같은 리뷰의 🟡💡도 반영: `gh pr ready`·`gh alias set` 차단, `--draft --draft=false`(gh는 마지막 값 사용) 차단, PR 본문에 리뷰 원문 대신 요약
4. **ship 첫 실전에서 오탐: `git push -u origin agent/0-... 2>&1`이 차단** — 리다이렉트 `2>&1`을 push 대상(refspec)으로 읽음. 허용 목록으로 바꾸면서 생긴 부작용(전에는 main인지만 봐서 드러나지 않음). 리다이렉트 토큰을 건너뛰게 수정 (테스트 3개 실패 확인 → 수정, `main 2>&1`은 계속 차단 확인)
   - 3차 리뷰(승인, 🟡): 이 수정이 새 구멍을 만듦 — `"> 파일"`의 파일까지 건너뛰게 했더니 `git push origin ">" main`(따옴표 속 `>`는 리다이렉트가 아닌 진짜 refspec)으로 대상을 숨길 수 있었다. 토큰화가 따옴표를 벗겨 둘을 구분 못 하므로, 리다이렉트 토큰 **자체만** 건너뛰게 단순화. 떨어진 `> push.log`는 차단되는 안전한 오탐으로 남김 (`>push.log`, `2>&1`은 통과)
   - 4차 리뷰(승인, 🟡): 같은 원인의 변형 `git push origin "2>x:main"`, `">main"`이 여전히 통과 → 증상이 아니라 **원인**(따옴표를 벗긴 뒤에 판정)을 고침: git 명령은 `_tokens(..., drop_redirects=True)`로 따옴표가 남아 있을 때 리다이렉트를 걸러낸다. 따옴표로 시작하는 토큰은 리다이렉트로 보지 않음
   - 교훈: 리뷰 지적을 하나씩 막으면 같은 부류가 계속 나온다 (3차 → 4차). 두 번째 비슷한 지적이 오면 원인으로 거슬러 올라간다
   - 교훈: 단위 테스트 표는 "사람이 쓰는 깔끔한 명령"뿐이었다. 에이전트가 실제로 붙이는 꼬리(`2>&1`, `| tail`)도 표에 넣어야 한다. 도그푸딩이 이걸 잡았다
   - 교훈: 허용 목록으로 바꿔도 "명령이 실제로 무엇을 건드리는가"(--all)와 "같은 명령의 다른 이름"(별칭)은 따로 봐야 한다

### 알려진 한계
- 리뷰 5차(승인)에서 남은 것: `2>C:/tools/git.exe`처럼 리다이렉트 대상이 git 경로이면 guard가 IndexError → run_guard가 차단 (안전한 쪽 실패, 이유 메시지만 엉뚱함). 떨어진 `> push.log`, PowerShell `*>`도 차단되는 오탐 → **이슈 #3에서 해결** (연산자만 있는 토큰이면 다음 토큰을 파일 이름으로 버림. IndexError는 현재 코드에서 재현되지 않음). PowerShell `*>`는 **일부러 차단 유지**: bash에서 `*`는 glob이라 `main` 파일이 있으면 main이 push 인자가 된다 (Phase 4 실패 9)
- 리뷰 2차(승인)에서 남은 것 — 후속 과제: `gh alias import`(alias set과 같은 부류), `gh pr create --draft -d=false`, `gh api ... pulls/1/merge`·graphql ready 전환
- heredoc 본문 속 명령 문자열(`gh pr new` 등)도 guard가 실제 명령으로 보고 막는다 (보수적 동작). 테스트 데이터는 파일 도구로 넘긴다
- guard는 **명령줄 인자만** 본다: `git -c push.default=upstream push`, `git branch -u origin/main` 후 `git push`, `remote.origin.push` 설정으로 대상 바꾸기, `gh api repos/o/r/pulls`로 draft 아닌 PR 만들기는 못 막음 → 최종 경계는 GitHub Ruleset과 사람 머지
- 이 브랜치의 Phase 1~2 리뷰(1~4차)는 리뷰 로그 도입 전이라 PR #1 본문은 이 문서 기록을 근거로 작성

---

## Phase 4. GitHub Actions 루프 — 2026-10-30

### 만든 것
| 워크플로 | 트리거 | 하는 일 | 권한 |
|---|---|---|---|
| `ci.yml` | `pull_request`, `workflow_call(pr)` | pytest·ruff·format·mypy, PR 500줄 상한 | contents·PR 읽기 |
| `agent-spec.yml` | 소유자가 `agent:spec` 라벨 | SPEC 초안을 이슈 댓글로 (표식 `<!-- agent-spec -->`) | issues 쓰기 |
| `agent-build.yml` | 소유자가 `agent:build` 라벨 | tdd → 게이트 → reviewer → commit → ship, 그다음 ci·review 호출 | contents·PR·issues 쓰기 |
| `claude-review.yml` | `pull_request`(소유자·같은 저장소), `workflow_call(pr)` | 리뷰 댓글 하나 (`<!-- claude-review -->`) | contents 읽기, PR 댓글 |
| `agent-fix.yml` | 소유자가 agent/* PR에 `@claude` 댓글 | 라운드 검사 → 반영 → push, 그다음 ci·review 호출 | contents·PR·issues 쓰기 |

### 설계
| 결정 | 이유 |
|---|---|
| SPEC 승인을 라벨 2단계로 (사용자 결정) | 로컬의 "SPEC 승인 후 구현"을 CI에서도 유지. 방향이 틀린 이슈에 구현 비용을 쓰지 않음 |
| 인증 = 구독 OAuth 토큰 (사용자 결정, `claude setup-token`) | 별도 과금 없음. 사용자가 Secrets에 직접 등록 |
| prompt에는 **이슈·PR 번호만** 넣는다 | 본문을 `${{ }}`로 보간하면 프롬프트 주입 + 스크립트 주입(`run:`) 통로. 본문은 에이전트가 `gh`로 읽는 자료 |
| 신뢰하는 SPEC = 소유자 또는 `github-actions[bot]`이 쓰고 표식이 있는 마지막 댓글 | 공개 저장소에서 아무나 "SPEC" 댓글을 달 수 있음 |
| 트리거는 `sender == repository_owner` (action의 write 권한 검사 위에 한 겹 더) | PLAN "저장소 소유자가 지정한 라벨"을 문자 그대로 |
| action에 `github_token: ${{ github.token }}` 전달, ci·review는 `workflow_call`로 직접 호출 | `GITHUB_TOKEN`으로 만든 push·PR은 워크플로를 트리거하지 않는다(GitHub 규칙). 앱 토큰으로 push하면 이벤트 트리거 + 직접 호출로 중복 실행 → 한 경로(직접 호출)로 고정. 봇 허용(`allowed_bots`) 0 |
| 수정 라운드 상한을 **워크플로 단계**가 표식 댓글 수로 센다 | Phase 2와 같은 원칙: 모델의 말이 아니라 기계가 센다. 작성자(`github-actions`)로 거르므로 남의 표식 댓글은 세지 않음 |
| 허용 도구를 워크플로마다 `--allowedTools`로 좁힘 | 실수와 흔한 주입을 줄이는 용도. **샌드박스가 아니다**: `python -m`으로 에이전트가 쓴 코드를 실행하면 그 안의 subprocess는 guard가 못 본다. 실제 경계는 소유자 라벨·job 토큰 권한·Ruleset required check |
| 머지의 기계적 경계 = Ruleset required check `check` + ci는 `ready_for_review`에도 실행 | `GITHUB_TOKEN` 이벤트는 워크플로를 트리거하지 않아 봇의 push·ready 전환으로는 PR head에 `check`가 생기지 않는다. job 권한에 checks·statuses가 없어 위조도 불가. 사람이 Ready로 바꿔야 머지 가능 |
| `concurrency`를 job 수준에 | workflow 수준이면 `if:`로 skip될 실행도 그룹에 들어가 대기 중인 정상 실행을 취소한다. 공개 저장소라 누구나 PR 댓글로 소유자의 fix 실행을 취소할 수 있었음 |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB: "1"` | 에이전트가 쓴 테스트·PR head의 훅이 OAuth 토큰을 환경변수로 읽어 공개 댓글에 올리는 경로 차단 (action 보안 문서의 변수). **Linux에서는 모든 명령을 bubblewrap 샌드박스에서 돌리게 한다** → 런타임을 워크플로에서 직접 설치 (실패 5) |
| 하네스 훅(guard·gate)을 CI에서도 그대로 사용 | 같은 `.claude/settings.json`. push는 `agent/*`만, 커밋 전 리뷰 필수, Stop 게이트 2회 재시도 |
| 재시도·비용 상한: max-turns(spec 15/build 40/review 20/fix 20), timeout-minutes, concurrency, fix 2라운드 | 구독 토큰은 로컬 작업과 사용 한도를 공유. API 키로 바꾸면 Console workspace 월 지출 한도를 걸 것. Actions 분은 공개 저장소라 무료 |

### 겪은 실패와 해결
1. **YAML 파싱 오류** — `run: gh ... --body "...: $RUN"`처럼 한 줄 값 안의 `": "`가 매핑으로 읽힘 → 블록 스칼라(`run: |`)로. 로컬에서 PyYAML로 5개 파일 파싱 확인
2. **리뷰 1차 🔴 4건** (스크립트 주입·fork 방어·workflow_call 문법은 통과)
   - 자동 머지 금지가 모델 순종에만 기댐 (`--allowedTools`는 샌드박스가 아님, Ruleset 필요 승인 0) → required check `check` + ci `ready_for_review`
   - workflow_call ci의 check는 호출 이벤트의 SHA(main HEAD)에 붙어 PR에 안 보이고, 권장 설정대로면 에이전트 PR을 영원히 머지 못 함 → 위와 같은 수정으로 "사람이 Ready → ci → 머지" 흐름 확정
   - workflow 수준 concurrency가 정상 실행을 조용히 취소(남의 댓글로 DoS 가능) → job 수준
   - "Actions가 PR 생성 허용" 저장소 설정 누락 → 사용자 설정 목록에 추가
   - 🟡 반영: subprocess env scrub, build 실패 후에도 만든 PR은 ci·review(`!cancelled()`), fix 상한 거부 시 재리뷰 안 함
3. **리뷰 2차(승인) 🟡 반영 중 발견: 워크플로가 커밋 전 리뷰 대상이 아니었다** — `_reviewable`이 `.py`·`.claude/`·pyproject만 봐서, 권한을 가장 많이 쥔 `.github/workflows/`가 리뷰 없이 커밋될 수 있었음 → 대상에 추가 (테스트 먼저 실패 확인)
4. **리뷰 3차(승인) 🟡: "SPEC이 라벨 이후 수정됐으면 멈춤"을 모델에게 맡김** — 에이전트의 도구로는 라벨 시각·수정 시각을 알 수 없어 실행 불가능한 지시였다 → 판단을 워크플로 `run:` 단계로 옮기고(REST `created_at`/`updated_at` 필드 확인 후), 검증된 SPEC만 `.claude/tmp/spec.md`로 넘김. 에이전트는 댓글을 뒤지지 않는다
   - 교훈: 안전 조건을 프롬프트에 쓰기 전에 "모델이 그 조건을 확인할 수단이 있는가"부터 본다. 없으면 기계(워크플로·훅)로
   - 교훈: "도구 허용 목록 = 경계"라고 착각했다. Phase 1에서 배운 "deny는 보안 경계가 아님"과 같은 실수를 CI에서 반복 → 최종 경계는 항상 서버 측(Ruleset·토큰 권한)
5. **리뷰가 초록불인데 댓글이 없음** — Secret 등록 후 claude-review가 `success`, 4턴, 권한 거부 0건, 댓글 0개. 기본 로그에는 에이전트 턴이 안 보여 `gh run rerun --debug`(전체 출력 자동 켜짐)로 다시 봄 → action의 "Install subprocess isolation dependencies"(bubblewrap·socat) 단계 조건이 `allowed_non_write_users != ''`로 **건너뜀**. 우리는 env로 SCRUB만 켜서, 샌드박스는 강제되는데 런타임이 없어 Bash(`gh`)가 실행되지 못한 것으로 판단 → 4개 워크플로에 같은 설치 단계(apt 3회 재시도, 실패 시 job 실패)를 추가 → 다음 실행에서 리뷰 댓글 게시 확인
   - 교훈: 보안 환경변수에도 런타임 의존이 있다. action이 그것을 **조건부로** 설치하면 우리 설정 경로에서는 빠질 수 있다 → action.yml의 `if:`를 읽는다
   - 교훈: "성공했는데 아무 일도 안 함"이 가장 늦게 발견된다. 후속: 리뷰 후 봇 댓글이 새로 생겼는지 확인하는 단계
   - 디버그 재실행 로그는 공개다(Secret은 `***` 마스킹). 확인 후 삭제 가능
6. **PR 자동 리뷰 1차 🔴: fork PR 가로채기** — build의 "만든 PR 찾기"가 브랜치 이름(`agent/<N>-`)만 봤다. 공개 저장소라 누구나 fork에서 같은 이름으로 PR을 미리 열 수 있고, build가 PR 없이 멈추는 정상 경로(모호함·에스컬레이션)에서 그 PR이 OAuth 토큰을 가진 review job으로 넘어간다. review의 fork 방어는 `pull_request` 경로에만 있었다 → build는 `isCrossRepository == false`만 고르고, review는 두 경로 모두 첫 단계에서 fork면 실패. 🟡 fix 라운드 작성자 비교 `startswith` → `==` (null 작성자 방어). jq 필터 3개는 실제 jq(파이썬 바인딩)로 경계 입력 확인
   - 교훈: 사람이 보는 이벤트(`pull_request`)에 건 방어를 기계 경로(`workflow_call`)에도 걸었는지 — 같은 job의 입구가 둘이면 검사도 둘
7. **PR #2가 자기 크기 제한(500줄)에 걸림** (503줄) → 사용자 결정: 사람용 문서(`*.md`)는 세지 않는다. 에이전트 동작을 바꾸는 md(`.claude/` 아래, 모든 `CLAUDE.md`)는 센다. 목적(사람이 검토할 수 있는 크기)은 유지
   - 한계: `pull_request` ci는 PR 쪽 ci.yml로 돌아, PR이 상한·검사를 바꾸면 자기 자신을 통과시킬 수 있다 → 워크플로 변경은 리뷰 필수 대상이고 사람이 머지 전에 본다

8. **첫 실전 루프(이슈 #3)에서 build가 guard.py를 못 고침** — SPEC 단계는 성공(11턴, $0.16, 인수조건 12개). build는 7턴 만에 "권한 정책으로 `.claude/hooks/guard.py` 편집 거부"를 이슈에 남기고 멈췄고, "PR 없음" 알림도 정상 동작. 원인은 우리 deny가 아니라 Claude Code의 **보호 경로**: `.claude/`(와 `.git`) 쓰기는 `--allowedTools Edit`나 allow 규칙으로도 자동 승인되지 않는다(`bypassPermissions`에서만 풀림)
   - 결과적으로 좋은 성질: 주입된 CI 에이전트도 **자기를 감시하는 하네스(guard·gate·settings·스킬)는 못 고친다**. 하네스 수정은 사람 쪽(로컬) 작업 → #3은 로컬에서 TDD로 고침
   - 교훈: 루프 시험 과제는 하네스가 아니라 프로젝트 코드로 고른다. 그리고 진단 때 guard를 `guard.py`로 직접 돌려 "통과"를 봤는데, 진입점은 `run_guard.py`였다(아무것도 검사하지 않은 확인) → 훅 시험은 settings.json에 적힌 진입점으로

9. **이슈 #3 수정이 보안 회귀를 만듦 (로컬 reviewer 🔴)** — SPEC 인수조건 "`*> out.txt`면 허용"을 그대로 구현했더니, bash에서 `touch main` 후 `*> out.txt`를 붙인 agent 브랜치 push가 main까지 push하는 길이 열렸다(수정 전 guard는 차단). 인수조건이 셸 종류(PowerShell/bash)를 구분하지 않은 것이 원인 → `*` 접두어를 리다이렉트로 인정하지 않고 회귀 테스트를 BLOCKED에 추가
   - 교훈: 에이전트가 쓰고 사람이 승인한 SPEC도 틀릴 수 있다. 보안 코드에서 "허용을 늘리는" 인수조건은 우회 관점으로 따로 검토한다
   - 교훈: 이 수정 중 파이썬 일괄 치환 스크립트가 두 번째 치환에서 실패해 guard가 **중간 상태**로 남았다(테스트 1개 실패, 도구는 안 막힘). "guard는 한 번에 완결된 수정" 규칙을 일괄 치환으로 어겼다 → guard는 Edit 한 번(또는 전체 Write)으로
   - 교훈: 기록 문장을 heredoc으로 넘기자 guard가 본문 속 push 문장을 명령으로 읽어 차단했다(heredoc 본문 오탐) → 긴 텍스트는 파일로 쓰고 실행
   - 같은 리뷰에서 발견한 **기존 우회** (#3 이전부터): `SEGMENT_SPLIT`가 따옴표와 `>|`를 몰라, `>|` 리다이렉트나 따옴표 속 `;`를 섞은 main push가 허용된다. 서버 쪽 Ruleset(PR 필수)이 main을 막으므로 실제 피해는 없지만 guard 단독으로는 뚫림 → 후속 이슈 (하네스 코드라 로컬 작업)

10. **두 번째 실전 루프(이슈 #5, 프로젝트 코드)에서 build가 두 번 PR 없이 끝남**
   - 1차(6턴, $0.11): SPEC 질문 4개에 답이 없다며 질문 댓글을 남기고 멈춤 → 아래 "알려진 한계"의 SPEC 답 전달 빈틈이 실제로 터졌다. 소유자 승인(제안 모두 수락)을 "결정" 절로 바꾼 SPEC을 소유자 댓글로 다시 게시하고 라벨을 다시 붙임
   - 2차(16턴, $0.26, 권한 거부 1회): **성공으로 끝났는데 PR도 댓글도 없음**. 기본 로그에는 에이전트의 마지막 답변도, 무엇이 거부됐는지도 없어 원인을 알 수 없었다 → PR이 없을 때 실행 기록(`execution_file`)에서 마지막 답변과 거부된 도구의 대상(명령·파일 경로)만 로그에 남기는 단계를 추가. `show_full_output`은 도구 결과 전체가 공개 로그에 남아 쓰지 않는다
   - 진단 출력은 모델 출력이라 `::stop-commands::`로 워크플로 명령 해석을 끄고, 게이트 에스컬레이션(`continue:false`는 result에 안 남을 수 있음)을 보려고 gate-log의 block/escalate 줄(검사 이름만)도 출력 (reviewer 🟡)
   - 남은 가설: tdd 스킬이 `ruff`를 `python -m` 없이 불러 CI 허용 목록에 걸림(→ 고침), reviewer 미승인으로 commit 차단, 게이트 에스컬레이션. 16턴이면 ship 전에 멈췄을 가능성이 높다 → 다음 실행의 진단 출력으로 확정
   - 조사 중 확인한 확실한 버그: `ship`은 PR 본문을 `.claude/tmp/pr-body.md`에 Write로 쓰는데, `.claude/`는 보호 경로라 CI에서는 반드시 거부된다(실패 8과 같은 원인) → 본문 경로를 `tmp/pr-body.md`(gitignore)로 옮김
   - **3차(12턴, $0.27)에서 진단 단계로 원인 확정**: 마지막 답변이 "reviewer를 시작했고 결과를 기다리는 중". Agent 도구는 `run_in_background`를 생략하면 서브에이전트를 **백그라운드**로 띄운다(Agent SDK subagents 문서, v2.1.198부터). `-p` 실행은 메인 턴이 끝나면 세션도 끝나 리뷰 결과가 돌아오지 않았다. headless 문서에는 백그라운드 작업 대기 상한(`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`)이 있지만 이 경로에서는 동작하지 않은 것으로 보인다(claude-code 이슈 #73453과 같은 증상). 로컬에서는 결과 알림이 다음 턴을 깨워 문제가 없었다 → build·fix의 action env에 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (Agent 도구에서 `run_in_background`가 사라져 항상 결과를 받고 진행). 2차의 16턴도 같은 원인으로 보인다(그때는 진단이 없어 확정 불가)
   - **4차(37턴, $0.56)**: reviewer가 포그라운드로 돌아 승인 2회, pytest 206개 통과까지 갔지만 **커밋에서 guard가 "리뷰 필요"로 차단**. 리뷰 기록 훅이 `PostToolUse(SubagentHandback)`에만 걸려 있었는데, `SubagentHandback` 도구는 **auto 모드에서만** 제공된다(hooks 문서). 로컬은 auto 모드라 동작했고 CI(`-p`)에서는 보고서가 서브에이전트의 마지막 텍스트로 와서 기록되지 않았다 → `SubagentStop`(matcher `reviewer`)에도 `review-done`을 걸고, auto 모드에서 Handback 뒤 오는 맺음말이 승인을 덮어쓰지 않게 SubagentStop은 판정 줄이 있을 때만 기록 (테스트 3개, 덮어쓰기는 먼저 실패 확인). 에이전트는 상태 파일을 만들거나 guard를 고치지 않고 이유를 이슈에 남기고 멈췄다 — 우회하지 않는 것이 의도한 동작
   - 교훈: 로컬과 CI는 **권한 모드가 달라 쓸 수 있는 도구가 다르다**. 훅이 특정 도구 이름에 걸려 있으면 그 도구가 모든 모드에 있는지 확인한다
   - 교훈: 실패 5의 "성공했는데 아무 일도 안 함"이 다시 나왔다. 에이전트가 멈출 수 있는 모든 경로에서 **이유가 사람에게 보이는지**를 설계 때 확인한다 (프롬프트의 "멈추면 댓글"은 모델이 지킬 때만 동작)

### 검증 (실전, PR #2)
| 시도 | 결과 |
|---|---|
| `ci` (`pull_request` opened, Linux 러너) | **통과 18초** — 훅 테스트 154개가 Linux에서도 통과 (Windows 경로 케이스 포함) |
| `claude-review` (Secret 등록 전) | 실패: action 자체 검증 "ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN … is required" → 예상된 실패, 값이 비어 있음을 로그로만 확인 (토큰 출력 없음) |
| `claude-review` (Secret 등록 후) | `success`인데 댓글 없음 → 실패 5 |
| `claude-review` (샌드박스 런타임 설치 후) | **리뷰 댓글 게시** (❌ 수정 후 재검토, 🔴 1 · 🟡 3) → 실패 6. 이로써 확인: Claude GitHub App 없이 `github_token`만으로 동작, scrub 후에도 `GH_TOKEN` 유지(공식 문서와 일치), 비용 약 $0.06~0.09/회 |

### 사용자 설정 (저장소 설정·시크릿 → 사용자가 직접)
1. `gh auth refresh -s workflow` (Claude가 실행, 브라우저 승인만 사용자) 2. `CLAUDE_CODE_OAUTH_TOKEN` Secret (사용자) 3. 라벨 `agent:spec`·`agent:build` (Claude가 생성함) 4. Actions가 PR 생성 허용 (사용자) 5. **Ruleset required status check `check` (사용자, 필수)**

### 알려진 한계·확인할 것
- `issues`·`issue_comment` 워크플로는 **기본 브랜치(main)의 파일**로 실행된다 → 실전 검증은 이 PR이 머지된 뒤에 가능
- CI에서 프로젝트 훅이 실제로 도는지는 build 첫 실행 로그로 확인 (`settingSources`에 project 포함은 확인)
- 후속(이슈로): 워크플로 jq 필터를 `.github/scripts/`로 빼서 pytest로 회귀 검사, `actionlint`를 ci에, `id-token: write` 필요 여부
- **SPEC 질문에 대한 답이 build에 전달되지 않는다**: build는 표식 붙은 마지막 SPEC 댓글만 읽는다. 답이 제안과 다르면 소유자가 답을 반영한 SPEC을 표식과 함께 다시 게시해야 한다 (#3은 제안대로라 그대로 승인, #5에서 실제로 막힘 → 실패 10). 후속: spec 스킬이 질문마다 "제안"을 쓰고, 승인 = 제안 수락으로 문서화
- 리뷰 봇의 지적은 자료일 뿐이라 수정 범위는 소유자 댓글이 정하지만, 모델이 그 경계를 지키는지는 프롬프트에 의존
- 이슈 본문을 통한 프롬프트 주입은 근본적으로 못 막는다. 주입된 에이전트는 실행 경로와 `.git/config`의 토큰으로 job 권한(`contents`·`issues`·`pull-requests: write`)을 그대로 쓸 수 있다: main 외 브랜치·태그·릴리스 생성/삭제, 봇이 쓴 댓글 수정(다른 이슈의 SPEC 댓글 포함), 라운드 표식 삭제. 머지는 required check가 막고, SPEC 바꿔치기는 build 워크플로 단계가 막는다(봇 SPEC 댓글이 `created_at != updated_at`이면 거부, 고친 SPEC은 소유자 댓글로 재게시). 후속: 태그 Ruleset 보호
- 리뷰 4차(승인)에서 남은 것: 주입된 이전 run이 다른 이슈에 봇 이름으로 **새** SPEC 댓글을 달거나 소유자 SPEC 댓글을 지우면 수정 검사를 통과한다 → 후속: 봇 SPEC은 소유자의 👍 반응이 있어야 승인 (GITHUB_TOKEN으로는 소유자 반응을 못 만듦. 반응이 `updated_at`을 바꾸는지 먼저 확인). 그 전까지는 `agent:build` 전에 SPEC 댓글이 하나뿐인지 눈으로 확인
- 후속: spec.md 첫 줄에 SPEC 댓글 URL을 넣어 PR 본문 링크에 쓰기, action을 커밋 SHA로 고정 (`add[]`는 실패 6에서 실제 jq로 확인함)
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`의 목적은 **OAuth 토큰 보호**다. `GITHUB_TOKEN`은 이미 `.git/config`에서 읽을 수 있으므로 숨기는 대상이 아니라 job 권한·Ruleset으로 묶는 대상
- build·fix가 부른 리뷰 중에 소유자가 Ready를 누르면 진행 중 리뷰가 취소되고 build·fix run이 cancelled로 보인다 (새 리뷰는 돈다, 의도된 동작)
- `--max-turns`는 서브에이전트(reviewer) 턴을 세지 않는다 → 그 부분은 `timeout-minutes`만 막음
- ~~action을 `@v1` 태그로 사용 (커밋 SHA 고정은 후속 과제)~~ → 후속 처리 A에서 SHA 고정
- "만든 PR 찾기"는 이전 실행이 남긴 같은 이슈의 열린 PR도 집을 수 있음

---

## Phase 5. 관측과 개선 — 2026-10-31

### 만든 것
- `docs/LEARNING.md`: 환류 절차와 실패 패턴 표 (HARNESS 실패 약 40건을 9개 패턴으로 묶음)
- `.claude/hooks/observe.py`: gate-log.jsonl 요약 (결과별 횟수, block·escalate된 검사, 리뷰 거절률, 에스컬레이션 세션)
- CI 기록 보관: build·fix가 gate-log를 아티팩트 `gate-log`로 30일 동안 올림
- 환류 실행: "성공인데 조용히 끝남" → `결과 확인` 단계 (spec·review·fix) + 구조 테스트 `.github/scripts/test_workflows.py`

### 설계
| 결정 | 이유 |
|---|---|
| 두 번째 발생부터 강제 장치로. 강한 순서는 테스트 > 훅 > 워크플로 단계 > 문장 | Phase 1 회고와 같다: 말로만 한 지시는 방치된다. 첫 발생은 우연일 수 있어 기록만 한다 |
| 환류를 **구조 테스트**로 | 결과 확인 단계 자체는 기존 워크플로만 고친다. 테스트는 앞으로 만들 에이전트 워크플로까지 막는다 |
| "새 댓글"을 시각이 아니라 **댓글 id**로 판정 | 러너 시계와 GitHub 시계가 어긋나도 판정이 틀리지 않는다. id는 단조 증가 |
| 작성자는 REST 이름 `github-actions[bot]` (GraphQL은 `github-actions`) | 두 API를 섞으면 조건이 조용히 어긋난다. 테스트로 고정 |
| 판정 스크립트는 `env -u GH_TOKEN`으로 실행 | 토큰이 필요한 일(댓글 받기)과 판정을 분리 |
| claude-review에 실패 알림 추가 | build·fix가 workflow_call로 부르면 review job의 실패가 PR 체크에 안 보인다. 구조 테스트 (b) 조건이 이 누락을 잡는다 |
| observe.py는 hooks 폴더, 기본 경로는 스크립트 안 | 기존 테스트·mypy 대상에 그대로 들어감. 명령줄에 상태 폴더 경로가 나오지 않아 guard에 걸리지 않는다 |
| 아티팩트 `include-hidden-files: true` | upload-artifact는 숨김 파일을 기본으로 뺀다(공식 README, 현재 v7). `.claude/`는 숨김 폴더 |
| retro 스킬·대시보드는 만들지 않음 | 절차 하나와 표 하나로 충분. 필요해지면 그때 만든다 |

### 실패와 해결
1. HARNESS에 이 절을 셸 heredoc으로 덧붙이려다 guard에 막힘: 본문에 상태 폴더 경로 글자가 들어 있었다. Phase 3 한계에 적어 둔 보수적 동작 그대로다 → 문서는 파일 도구로 쓴다 (LEARNING: guard 오탐 패턴, 기존 대응으로 충분)
2. **reviewer 1차(승인) 🟡 5건 반영**
   - **검사받는 쪽이 판정 스크립트를 고칠 수 있었다**: spec·fix 에이전트는 Write 권한이 있고 `.github/scripts/`는 보호 경로가 아니다 → 에이전트 실행 전에 `$RUNNER_TEMP`로 복사해 둔 사본으로 판정
   - fix 결과 확인이 "봇 댓글 아무거나"로 통과했다. 그 사이 달린 리뷰 댓글이나 알림도 셀 수 있었다 → 프롬프트에 `<!-- agent-fix -->` 표식을 넣고 그 표식으로 확인
   - LEARNING 표: guard 잠김에 P4 9를 추가하고 상태를 `한계`로 바꿈(이유 기재), "안전 조건을 모델 순종에 맡김" 패턴 추가
   - observe.py: 없는 파일을 넘기면 조용히 0건 표를 내던 것 → stderr에 경고하고 exit 1 (테스트 먼저 실패 확인)
   - 💡도 반영: 구조 테스트가 `!failure()`와 `*.yaml`을 처리, ci mypy 대상에 `.github/scripts` 추가, 아티팩트 `overwrite: true`(재실행 시 이름 충돌 방지)
   - 교훈: 결과 확인 장치도 "검사받는 쪽이 검사기를 고칠 수 있는가"를 본다. Phase 4 실패 7(PR 쪽 ci.yml)과 같은 부류

### 검증
- TDD Red: 구조 테스트가 기존 워크플로 4개 job(build·fix·spec·review) 모두에서 실패하는 것을 확인 → 단계 추가 후 통과
- 구조 테스트 (b): claude-review에서 알림 단계를 뺀 YAML을 넣으면 "failure()로 알리는 단계가 없다"로 실패
- 일부러 실패시키기: 표식 없는 봇 댓글 JSON → `expect_comment.py` exit 1, 이유 출력
- 워크플로의 jq 식 `add | map(.id) | max // 0`: 실제 jq(파이썬 바인딩)로 빈 배열 → 0, 여러 페이지 → 최댓값 확인
- `observe.py`를 실제 로컬 로그에 실행 → 관측 메모 (LEARNING.md)
- 전체 pytest(193)·ruff·mypy 통과
- 아직 확인하지 못한 것: 실제 CI 실행 (`issues`·`issue_comment` 워크플로는 main의 파일로 돈다 → 머지 후 agent:spec 이슈 한 번)

### 알려진 한계
- 결과 확인은 "댓글이 **있다**"만 본다. 내용이 쓸모 있는지는 사람이 본다
- fix의 결과 확인: head가 바뀌었거나 봇 댓글이 있으면 통과. 라운드 표식은 기준 id보다 앞이라 세지 않는다
- review의 판정 스크립트는 PR head의 것이다. **PR이 `expect_comment.py`를 바꾸면 자기 자신을 통과시킬 수 있다**(P4 실패 7의 ci.yml 한계와 같은 부류). spec·fix는 에이전트 실행 전 사본을 쓴다(fix 사본은 PR head 기준이라 같은 실행 안의 변조만 막는다. 이전 라운드가 커밋한 변경은 review와 같은 한계). `.git/config` 토큰을 읽을 수 있는 것은 에이전트 단계에 이미 있는 위험과 같은 부류이고, fork PR은 기존 단계가 거부한다
- build의 "결과 확인 — 만든 PR 찾기"는 실패하지 않는 단계다. 판정은 다음 단계들의 `if`가 한다. 구조 테스트는 이름 규칙으로 통과한다
- 공개 저장소의 아티팩트는 로그인한 누구나 받을 수 있다. gate-log에는 reviewer 요약이 들어간다 (PR 본문에도 쓰이는 내용이고 시크릿은 없음)
- 로컬 gate-log는 이 PC에만 있다. 여러 PC에서 작업하면 따로 모아야 한다

---

## 후속 처리 (Phase 1~5 이후)

### A. 워크플로 공급망 — 2026-10-31
- 외부 action 4종(claude-code-action v1, checkout v6, setup-python v6, upload-artifact v7)을 **커밋 SHA**로 고정. 태그는 주석으로 남긴다. SHA는 `gh api repos/<r>/commits/<tag>`로 확인
  - 이유: 태그는 옮겨질 수 있다. 이 job들은 쓰기 권한 GITHUB_TOKEN과 OAuth 토큰을 쥔다
  - 메이저 버전은 올리지 않았다(checkout·setup-python은 v7이 나와 있음). 올리는 것은 별도 변경으로
- 구조 테스트 `test_external_action_is_pinned_to_commit_sha`: 외부 `uses:`(job 수준 재사용 워크플로 포함, `./` 제외)는 40자리 SHA여야 한다. 고정 전 16개 실패 확인 → 고정 후 통과
- ci에 **actionlint v1.7.12**: 릴리스 checksums.txt의 sha256을 워크플로에 고정하고 검증한 뒤 실행. ubuntu 러너의 shellcheck도 함께 돈다
  - 로컬 사전 실행(windows 바이너리 체크섬 검증, shellcheck-py): 지적 1건. ci의 `mypy $(ls -d …)`는 의도된 단어 분리라 이유를 달아 SC2046 무시
- 한계: SHA를 올리는 것은 사람 몫이다(Dependabot 미설정). actionlint 다운로드는 GitHub 릴리스에 의존하지만 체크섬이 맞지 않으면 실패한다
- 한계 (리뷰 🟡): 구조 테스트는 `workflows/`만 본다. composite action(`.github/actions/*/action.yml`)을 만들면 glob을 넓힌다. `docker://` uses는 지금 정규식에서 항상 실패(fail closed)하므로 쓰게 되면 `@sha256:` digest 형식을 따로 허용한다. 러너에 shellcheck가 빠지면 actionlint는 그 검사만 조용히 건너뛴다
- SHA를 올릴 때는 `commits/<tag>`의 커밋 SHA를 쓴다. annotated 태그(claude-code-action v1)는 `git/ref/tags`의 `object.sha`가 태그 객체라 다르다
