# branch-name

## 목적 / 역할
> 이슈 번호와 제목으로 `agent/<번호>-<slug>` 브랜치 이름을 결정적으로 만드는 순수 함수.

## 인터페이스
- `make_branch_name(number: int, title: str) -> str` (`from branch_name import make_branch_name`)
- 번호 ≤ 0 → `ValueError`

## 의존성 / 연관 모듈
- 의존: 표준 라이브러리 `re`만
- 사용됨: 없음 (ship 스킬 연결은 범위 밖, 사람이 한다)

## 기술 결정 사항
- slug: ASCII 영문·숫자만 유지(한글·악센트는 구분자), 최대 30자(접두사 제외)
- 30자 초과 시 31자까지 보고 마지막 하이픈 앞에서 자른다. 하이픈이 없으면 30자에서 자른다
- 빈 slug는 `issue`
