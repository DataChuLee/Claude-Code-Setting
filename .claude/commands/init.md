# /init — 새 프로젝트 초기화

**사용법**: `/init "프로젝트명"`

## 실행 순서

1. 현재 디렉토리에 프로젝트 기본 구조 생성
   ```
   {프로젝트명}/
   ├── src/
   │   └── __init__.py
   ├── tests/
   │   └── __init__.py
   ├── CLAUDE.md       ← 템플릿 복사 후 자동 채움
   ├── TODO.md         ← 템플릿 복사
   ├── pyproject.toml  ← ruff 설정 포함
   └── .gitignore
   ```
2. `CLAUDE.md` — 프로젝트명, 기술 스택 기본값 자동 입력 후 사용자에게 확인
3. `pyproject.toml` — ruff, pytest 설정 기본값으로 생성
4. `.gitignore` — Python 표준 gitignore 생성
5. `git init` + 초기 커밋
6. `@builder`에게 아키텍처 설계 시작 여부 확인

## 생성되는 pyproject.toml 기본값

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## 주의사항
- 이미 존재하는 파일은 덮어쓰지 않음
- `git init`은 `.git`이 없을 때만 실행

## 예시
```
/init "my-api"
/init "shopping-cart-service"
```
