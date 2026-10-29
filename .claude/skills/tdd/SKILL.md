---
name: tdd
description: "기능을 TDD(Red → Green → Refactor)로 구현한다. 테스트를 먼저 쓰고, 통과하는 최소 코드를 작성하고, 기능 폴더의 SPEC/CLAUDE/TODO 문서를 갱신한다. 이 프로젝트에서 기능 구현·버그 수정 시 기본 작업 흐름."
when_to_use: "'~ 만들어줘', '~ 구현해줘', '기능 추가', '테스트 먼저', 'TDD로', '테스트 코드 작성', 'pytest', 'Red-Green-Refactor' 같은 요청. 예: '덧셈 함수 만들어줘', '검색 기능 TDD로 구현해줘'"
argument-hint: "[기능명]"
---

# TDD — Red → Green → Refactor

대상 기능: $ARGUMENTS

## 순서
1. **기능 폴더 준비** `src/<기능>/`이 없으면 만들고 템플릿을 복사한다 (있는 파일은 덮어쓰지 않음)
   - `.claude/templates/FEATURE_SPEC.md` → `src/<기능>/SPEC.md` (요구사항·인수조건)
   - `.claude/templates/FEATURE_CLAUDE.md` → `src/<기능>/CLAUDE.md` (기능 지도)
   - `.claude/templates/FEATURE_TODO.md` → `src/<기능>/TODO.md` (작업 체크리스트)
   - SPEC.md가 `승인됨`이 아니면 `spec` 스킬로 작성·승인부터 받는다 (승인 전 구현 금지)
2. **Red** — `builder` 에이전트가 SPEC의 인수조건마다 테스트를 `tests/test_<기능>.py`에 작성
   - 이름: `test_<동작>_<조건>_<결과>` (테스트 이름만 읽어도 스펙이 되게)
   - 정상 / 경계값(0, 빈 값, 최대) / 예외 케이스
   - `python -m pytest tests/test_<기능>.py` → **실패 확인**
3. **Green** — 테스트를 통과하는 최소 코드 작성 → `python -m pytest` 통과 확인
4. **Refactor** — 테스트를 유지한 채 정리 → `ruff check --fix . && ruff format .`
5. **문서 갱신** — TODO.md 완료 항목 체크, CLAUDE.md에 실제 인터페이스·결정 사항 반영
   (`src/<기능>/` 코드를 바꾸고 TODO.md를 안 바꾸면 Stop 게이트가 막는다)
6. LLM 출력이 들어가는 부분은 `eval` 스킬로 평가 → 그다음 `review` → `commit`

## 게이트 (훅이 강제 — 말로 약속하지 않아도 됨)
- 응답을 끝낼 때 Stop 게이트가 pytest·ruff·mypy·TODO를 검사. 실패하면 되돌려 보냄 (최대 2회, 3번째엔 멈추고 사람 호출)
- Red 단계에서 의도적으로 실패한 채로 응답을 끝내면 게이트가 막는다 → Red는 같은 턴 안에서 Green까지 간다

## 규칙
- 한 번에 기능 하나. 테스트가 통과하기 전에 다음 기능으로 넘어가지 않는다
- 막히면 테스트를 더 작은 단위로 쪼갠다
- `python -m pytest`로 실행한다 (import 경로 문제 방지)
