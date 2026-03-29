---
description: "REST API 컨벤션 적용. 'API 만들어줘', 'endpoint 추가', 'request/response 설계', 'FastAPI 라우터', 'HTTP 메서드' 요청 시 트리거."
---

# API Conventions Skill

## 응답 구조 통일

모든 API 응답은 아래 구조를 따른다.

```python
# 성공 응답
{
    "data": { ... },      # 실제 데이터
    "error": None,
    "meta": {             # 페이지네이션 등 부가 정보 (필요 시)
        "total": 100,
        "page": 1,
        "size": 20
    }
}

# 실패 응답
{
    "data": None,
    "error": {
        "code": "INVALID_INPUT",
        "message": "이메일 형식이 올바르지 않습니다."
    },
    "meta": None
}
```

---

## HTTP 메서드 규칙

| 메서드 | 용도 | 예시 |
|--------|------|------|
| GET | 조회 | GET /users/{id} |
| POST | 생성 | POST /users |
| PUT | 전체 수정 | PUT /users/{id} |
| PATCH | 부분 수정 | PATCH /users/{id} |
| DELETE | 삭제 | DELETE /users/{id} |

---

## URL 네이밍 규칙

```
# 복수형 명사 사용
GET  /users          ← 목록
GET  /users/{id}     ← 단건
POST /users          ← 생성

# 중첩 리소스
GET /users/{id}/orders
GET /users/{id}/orders/{order_id}

# 동사 금지 (동사는 HTTP 메서드로 표현)
❌ POST /createUser
✅ POST /users
```

---

## FastAPI 라우터 패턴

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

class UserCreateRequest(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    data: dict | None = None
    error: dict | None = None
    meta: dict | None = None

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest):
    # 구현
    return UserResponse(data={"id": 1, "email": body.email})
```

---

## 에러 처리 규칙

```python
# 커스텀 Exception 클래스 사용
class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# 예시
raise AppException("USER_NOT_FOUND", "사용자를 찾을 수 없습니다.", 404)
```

---

## HTTP 상태 코드 가이드

| 코드 | 상황 |
|------|------|
| 200 | 성공 (GET, PUT, PATCH) |
| 201 | 생성 성공 (POST) |
| 204 | 삭제 성공 (DELETE) |
| 400 | 잘못된 요청 |
| 401 | 인증 필요 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 422 | 유효성 검증 실패 |
| 500 | 서버 에러 |
