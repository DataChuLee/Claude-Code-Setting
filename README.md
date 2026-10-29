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
│   ├── guard.py              ← 위험 명령·시크릿 접근 차단 (PreToolUse)
│   └── test_guard.py         ← guard 차단/허용 테스트
├── skills/                   ← 자연어로 자동 실행, /이름 으로도 호출 가능
│   ├── tdd/                  ← SPEC 승인 → Red → Green → Refactor
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

## 안전장치

| 층 | 무엇 | 막는 것 |
|---|---|---|
| 1 | `settings.json` deny | 흔한 형태의 위험 명령, 시크릿 파일 |
| 2 | `guard.py` (PreToolUse) | 변형된 명령까지 문자열·현재 브랜치로 검사 |
| 3 | GitHub 브랜치 보호 | 서버 측 최종 경계 (사용자가 직접 설정) |

## 기술 스택
Python 3.11+ · pytest · ruff · FastAPI(선택)
