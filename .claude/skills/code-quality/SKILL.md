---
description: "코드 품질 기준 적용. '린트', '포맷', 'ruff', '코드 스타일', 'import 정리', 'type hint' 요청 시 트리거."
---

# Code Quality Skill

## 도구: ruff (린트 + 포맷 통합)

ruff 하나로 flake8 + isort + black을 대체한다.

```bash
# 린트 체크
ruff check .

# 린트 자동 수정
ruff check --fix .

# 포맷 체크
ruff format --check .

# 포맷 자동 적용
ruff format .

# 전체 (린트 수정 + 포맷)
ruff check --fix . && ruff format .
```

---

## ruff 설정 (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]
ignore = ["E501"]  # line too long (line-length로 제어)

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

---

## 코드 스타일 규칙

### Type Hints — 필수
```python
# ❌ 타입 없음
def get_user(user_id):
    pass

# ✅ 타입 명시
def get_user(user_id: int) -> dict | None:
    pass
```

### Import 순서 (isort 기준)
```python
# 1. 표준 라이브러리
import os
from typing import Optional

# 2. 서드파티
from fastapi import HTTPException
from pydantic import BaseModel

# 3. 로컬
from src.models import User
from src.utils import hash_password
```

### 명명 규칙
```python
# 변수/함수: snake_case
user_name = "홍길동"
def get_user_by_id(user_id: int): ...

# 클래스: PascalCase
class UserService: ...

# 상수: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DATABASE_URL = "postgresql://..."

# Private: 언더스코어 prefix
def _internal_helper(): ...
```

### 함수 길이
- 한 함수는 한 가지 일만
- 20줄 초과 시 분리 검토
- 중첩 depth는 3 이하 유지

---

## 품질 체크 순서
1. `ruff check --fix .` — 린트 자동 수정
2. `ruff format .` — 포맷 적용
3. `pytest` — 테스트 통과 확인
4. 커밋
