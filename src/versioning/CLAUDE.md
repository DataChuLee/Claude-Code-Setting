# versioning

## 목적 / 역할
> `MAJOR.MINOR.PATCH` 버전 문자열의 다음 버전을 계산한다.

## 인터페이스
- `versioning.bump.bump(version: str, part: str) -> str`
- 잘못된 버전·부분 이름·비문자열 입력은 모두 `ValueError`

## 의존성 / 연관 모듈
- 의존: 표준 라이브러리(`re`)
- 사용됨: (없음)

## 기술 결정 사항
- 정규식 `0|[1-9][0-9]*` + `re.ASCII`·`fullmatch`로 엄격 검증 (앞자리 0, 전각 숫자, 접미사, 끝 개행 거부)
- 상세는 SPEC.md `## 결정`
