# My Claude Code Setting

AI-Native Development 하네스 템플릿 (Python).
사람은 의도를 말하고 승인만 하며, 작업 흐름은 스킬이, 안전장치는 훅이 맡는다.
전체 로드맵: [docs/PLAN.md](docs/PLAN.md) · 설계 기록: [docs/HARNESS.md](docs/HARNESS.md)

## 구조

```
.claude/
├── CLAUDE.md                 ← 하네스 지도 (작업 흐름·금지 사항)
├── settings.json             ← permissions.deny + PreToolUse 훅 등록
├── hooks/
│   ├── run_guard.py          ← PreToolUse 진입점 (guard 고장 시 guard 수정만 허용)
│   ├── guard.py              ← 위험 명령·시크릿 접근·리뷰 없는 커밋 차단 규칙
│   ├── gate.py               ← 검증 게이트: Stop(재시도 2회)·ruff 즉시 피드백·리뷰 기록
│   └── test_*.py             ← 훅 테스트 (python -m pytest 에 포함)
├── skills/                   ← 자연어로 자동 실행, /이름 으로도 호출 가능
│   ├── spec/                 ← 요구사항·인수조건 → 사람 승인 (SDD)
│   ├── tdd/                  ← Red → Green → Refactor
│   ├── eval/                 ← LLM 기능: 평가셋·채점기 먼저 (Eval-Driven)
│   ├── gate-reset/           ← 사람만 실행: 게이트 재시도 횟수 초기화
│   ├── review/               ← reviewer 에이전트로 리뷰 → TODO.md 기록
│   ├── doc/                  ← docstring·README·API 문서
│   ├── commit/               ← ruff + pytest + 로컬 커밋 (push 안 함)
│   ├── scaffold/             ← 새 프로젝트 뼈대
│   ├── api-conventions/      ← REST API 규칙 (참고 지식)
│   └── code-quality/         ← ruff 기준 (참고 지식)
├── agents/
│   ├── builder.md            ← 설계 + 테스트 먼저 작성
│   └── reviewer.md           ← 리뷰 + 문서화
└── templates/                ← CLAUDE.md, FEATURE_SPEC/CLAUDE/TODO.md
```

## 새 프로젝트 시작

```bash
git clone https://github.com/DataChuLee/Claude-Code-Setting.git my-project
cd my-project
rm -rf .git && git init
```

그 다음 Claude Code에서 평소 말투로:
```
"my-project 프로젝트 세팅해줘"        → scaffold
"문서 검색 기능 만들어줘"             → tdd (SPEC 초안 → 승인 → 테스트 → 구현)
"리뷰해줘" / "문서화해줘" / "커밋해줘" → review / doc / commit
```

## 기능 폴더

```
src/<기능>/
├── SPEC.md    ← 요구사항·인수조건 (사람이 승인)
├── CLAUDE.md  ← 기능 지도 (이 폴더 파일을 읽을 때 자동 로드)
└── TODO.md    ← 작업 체크리스트·리뷰 기록
```

## 검증 게이트

| 언제 | 무엇 | 실패하면 |
|---|---|---|
| .py 저장 직후 | ruff | 즉시 Claude에게 오류 전달 |
| 응답 종료 시 | pytest · ruff · mypy · 기능 TODO.md 갱신 | 2회까지 되돌려 고치게 함, 3번째엔 멈추고 사람 호출 (`/gate-reset`) |
| 커밋 시 | reviewer가 본 코드 = 지금 코드 | 커밋 차단 |

## 안전장치

| 층 | 무엇 | 막는 것 |
|---|---|---|
| 1 | `settings.json` deny | 흔한 형태의 위험 명령, 시크릿 파일 |
| 2 | `guard.py` (PreToolUse) | 변형된 명령까지 문자열·현재 브랜치로 검사 |
| 3 | GitHub 브랜치 보호 | 서버 측 최종 경계 (사용자가 직접 설정) |

## 기술 스택
Python 3.11+ · pytest · ruff · FastAPI(선택)
