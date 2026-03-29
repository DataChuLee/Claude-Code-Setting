---
description: "TDD 루프 가이드. '/tdd 기능명', '테스트 먼저', 'pytest', '테스트 코드 작성', 'Red-Green-Refactor' 요청 시 트리거."
---

# TDD Cycle Skill

## 원칙: Red → Green → Refactor

테스트를 먼저 작성하고, 통과시키고, 정리한다.
구현 코드보다 테스트 코드가 항상 먼저다.

---

## 단계별 절차

### 1단계 — Red (실패하는 테스트 작성)
- 구현하려는 기능의 동작을 테스트로 먼저 정의
- 테스트는 지금 당장 실패해야 정상 (구현이 없으니까)
- 파일명 규칙: `test_{기능명}.py`

```python
# 예시: test_cart.py
def test_cart_total_with_discount():
    cart = Cart()
    cart.add_item(price=10000, qty=2)
    total = cart.calculate_total(discount_rate=0.1)
    assert total == 18000
```

### 2단계 — Green (테스트 통과하는 최소 구현)
- 테스트를 통과시키는 가장 단순한 코드만 작성
- 깔끔함보다 통과가 먼저
- pytest 실행 → 통과 확인

### 3단계 — Refactor (코드 정리)
- 테스트가 통과된 상태에서 코드 품질 개선
- 리팩터 후에도 테스트가 통과해야 함
- ruff로 린트/포맷 체크

---

## pytest 명령어

```bash
# 전체 테스트
pytest

# 특정 파일
pytest test_{기능명}.py

# 상세 출력
pytest -v

# 실패 시 즉시 중지
pytest -x

# 커버리지 포함
pytest --cov=. --cov-report=term-missing
```

---

## 파일 구조 규칙

```
프로젝트/
├── src/
│   └── {모듈명}.py        ← 구현 코드
└── tests/
    └── test_{모듈명}.py   ← 테스트 코드
```

---

## 주의사항
- 한 번에 하나의 기능만 TDD
- 테스트 하나 작성 → 구현 → 통과 → 다음 테스트
- 테스트가 너무 크면 더 작은 단위로 쪼갤 것
