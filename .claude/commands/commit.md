# /commit — 린트 + 포맷 + 커밋 + 푸시

**사용법**: `/commit` 또는 `/commit "커밋 메시지"` 또는 `/commit --no-push`

## 실행 순서

1. `ruff check --fix .` — 린트 자동 수정
2. `ruff format .` — 포맷 적용
3. `pytest` — 테스트 전체 통과 확인
4. 실패 시 → 중단, 문제 보고
5. 통과 시 → 변경된 기능 폴더의 `CLAUDE.md` 업데이트
   - 실제 구현된 API 엔드포인트, 의존성, 기술 결정 사항 반영
6. 변경된 기능 폴더의 `TODO.md` 업데이트
   - 완료된 항목 DONE으로 이동, BLOCKER 해소 여부 확인
7. 루트 `CLAUDE.md` 업데이트 — 새 기능/변경 사항 반영 (필요 시)
8. `git add -p` 또는 변경 파일 스테이징
9. `git commit -m "{메시지}"`
10. `git push` — 원격 저장소에 푸시 (`--no-push` 옵션 시 생략)

## 커밋 메시지 규칙
메시지 없이 실행하면 변경 내용을 분석해 자동 생성.

```
feat: 장바구니 총액 계산 기능 추가
fix: 할인율 0 입력 시 오류 수정
refactor: CartService 메서드 분리
test: 장바구니 경계값 테스트 추가
docs: 결제 API 엔드포인트 문서 추가
```

## 주의사항
- 테스트 실패 시 커밋 차단
- 린트 오류 자동 수정 후 커밋
- push 실패 시 커밋은 유지되며 push 오류만 보고
- CLAUDE.md/TODO.md 변경도 같은 커밋에 포함

## 예시
```
/commit
/commit "feat: 사용자 로그인 API 구현"
/commit --no-push
/commit "fix: 버그 수정" --no-push
```
