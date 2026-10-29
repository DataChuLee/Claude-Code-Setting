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
| 단위 테스트 | `python -m pytest` → 122 passed (`.claude/hooks` 포함) |

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
