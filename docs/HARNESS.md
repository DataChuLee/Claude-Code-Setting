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

### 검증 결과
**단위 테스트**: `python -m pytest .claude/hooks/test_guard.py -W error` → **67 passed**

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
