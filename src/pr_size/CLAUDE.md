# pr_size

## 목적 / 역할
> `pulls/{n}/files` 응답에서 PR 크기 제한에 셀 줄 수(additions+deletions)를 계산한다. ci.yml의 jq 규칙을 테스트 가능한 Python으로 옮긴 것.

## 인터페이스
- `pr_size.count_lines(data) -> int` — 항목 배열 또는 페이지 배열의 배열. 형식이 잘못되면 `ValueError`
- CLI: `python -m pr_size <JSON 파일>` → stdout에 숫자 하나. 오류는 stderr + 종료 코드 1(사용법 오류 2)
- 파일: `counter.py`(규칙) · `__main__.py`(CLI)

## 의존성 / 연관 모듈
- 의존: 표준 라이브러리만
- 사용됨: 아직 없음 (ci.yml 연결은 사람 몫)

## 기술 결정 사항
- `.md`는 안 센다. 단 `.claude/` 아래, 이름이 정확히 `CLAUDE.md`인 파일은 센다 (jq의 접미사 일치와 다름)
- 확장자 대소문자 구분(`.MD`는 센다), rename은 새 filename만 본다
- 잘못된 입력은 조용히 0이 아니라 오류 (bool은 정수로 보지 않음)
