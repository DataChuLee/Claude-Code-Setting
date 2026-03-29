# /doc — 문서화

**사용법**: `/doc` 또는 `/doc {파일명 또는 기능명}`

## 실행 순서

1. 대상 파일/기능을 **[reviewer agent]**에 전달
2. docstring, README 섹션, API 문서 작성
3. 작성 완료 목록 출력

## 문서화 대상
- 인자 없이 실행: 마지막으로 완성된 기능 자동 감지
- 파일 지정: `/doc src/auth/service.py`
- 기능 지정: `/doc 사용자 인증 모듈`

## 생성되는 문서
- 함수/클래스 **docstring**
- **README** 섹션 (기능 설명 + 사용 예시)
- **API 엔드포인트** 문서 (FastAPI 사용 시)

## 예시
```
/doc
/doc src/cart/
/doc 장바구니 기능
```
