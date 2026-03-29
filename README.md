# My Claude Code Setting

프로젝트별 Claude Code 자동화 환경 템플릿.
`git clone` 후 바로 사용 가능.

## 구조

```
.claude/                      ← Claude Code 자동화 설정 전체
├── skills/
│   ├── tdd-cycle/            ← TDD 루프 가이드 (자동 감지)
│   ├── api-conventions/      ← REST API 컨벤션 (자동 감지)
│   └── code-quality/         ← ruff 린트/포맷 기준 (자동 감지)
├── agents/
│   ├── tester.md             ← 테스트 작성 전문
│   ├── reviewer.md           ← 코드 리뷰 전문
│   ├── architect.md          ← 아키텍처 설계 전문
│   └── documenter.md         ← 문서화 전문
├── commands/
│   ├── tdd.md                ← /tdd → TDD 전체 루프
│   ├── review.md             ← /review → 리뷰어 호출
│   ├── doc.md                ← /doc → 문서화 호출
│   └── commit.md             ← /commit → ruff+pytest+커밋
├── hooks/
│   ├── post-write.ps1        ← 파일 저장 시 pytest 자동 실행
│   └── on-stop.ps1           ← 응답 완료 후 ruff 자동 실행
├── templates/
│   ├── CLAUDE.md             ← 프로젝트 루트에 복사 후 수정
│   └── TODO.md               ← 기능 폴더마다 복사 후 수정
└── settings.json             ← hooks 설정
```

## 새 프로젝트 시작

```bash
git clone https://github.com/DataChuLee/Claude-Code-Setting.git my-project
cd my-project
rm -rf .git   # 기존 history 제거
git init      # 새 프로젝트로 시작
```

그 다음:
```
1. .claude/templates/CLAUDE.md → 프로젝트 루트/CLAUDE.md 로 복사 후 수정
2. .claude/templates/TODO.md → 기능 폴더/TODO.md 로 복사 후 수정
3. Plan Mode (Shift+Tab) → 전체 피처 설계
4. /tdd "첫 번째 기능" 으로 시작
```

## 명령어

| 명령어 | 역할 |
|--------|------|
| `/tdd "기능명"` | TDD 전체 루프 (테스트 먼저 작성 → 구현 → 통과) |
| `/review` | 완성된 코드 리뷰 |
| `/doc` | docstring + README 문서화 |
| `/commit` | ruff 체크 + pytest + git commit |

## Hooks 동작

| 이벤트 | 스크립트 | 동작 |
|--------|----------|------|
| Write (Python 파일 저장) | post-write.ps1 | pytest 자동 실행 |
| Stop (응답 완료) | on-stop.ps1 | ruff 체크 + 알림음 |

## 기술 스택 기준
- Python 3.11+
- pytest (테스트)
- ruff (린트/포맷)
- FastAPI (API, 선택)
