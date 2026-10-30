---
name: scaffold
description: "이 하네스로 새 Python 프로젝트의 기본 구조(src/, tests/, CLAUDE.md, pyproject.toml, .gitignore)를 만든다."
when_to_use: "'새 프로젝트 시작', '프로젝트 초기화', '프로젝트 세팅해줘', '뼈대 만들어줘', 하네스를 clone한 직후. 예: 'rag-qa 프로젝트 세팅해줘'"
argument-hint: "[프로젝트명]"
---

# Scaffold

프로젝트명: $ARGUMENTS

## 순서
1. 구조 생성 (있는 파일은 덮어쓰지 않음)
   ```
   src/__init__.py
   tests/__init__.py
   CLAUDE.md        ← .claude/templates/CLAUDE.md 를 채움. 30줄 이내 프로젝트 지도 (하네스 규칙은 .claude/CLAUDE.md)
   pyproject.toml   ← 하네스에 이미 있음. [project] name만 프로젝트명으로 바꾸고, 필요한 의존성 추가
   .gitignore       ← 하네스 루트 .gitignore 그대로
   ```
   개발 도구 설치: `python -m pip install -e ".[dev]"` (pytest·ruff·mypy — 게이트가 `python -m`으로 부름)
2. CLAUDE.md의 프로젝트명·목적·기술 스택을 채우고 **사용자에게 확인**
3. `.git`이 없을 때만 `git init` + 초기 커밋
4. 첫 기능은 `src/<기능>/`에 SPEC·CLAUDE·TODO를 두고 `tdd` 스킬로 시작한다고 안내
