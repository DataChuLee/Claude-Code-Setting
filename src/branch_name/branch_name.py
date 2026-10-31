"""이슈 번호와 제목으로 `agent/<번호>-<slug>` 브랜치 이름을 만든다."""

import re

MAX_SLUG_LENGTH = 30
FALLBACK_SLUG = "issue"


def _slugify(title: str) -> str:
    # ASCII 영문·숫자 외 문자는 모두 구분자 → 하이픈 하나로 합치고 앞뒤 하이픈 제거
    # lower()를 먼저 하면 켈빈 기호(U+212A) 같은 비ASCII가 'k'로 바뀌므로 거른 뒤에 소문자화
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
    if len(slug) > MAX_SLUG_LENGTH:
        head = slug[: MAX_SLUG_LENGTH + 1]
        # 31번째 문자가 하이픈이면 앞 30자는 단어 경계에서 끝난다
        cut = head.rfind("-")
        slug = head[:cut] if cut > 0 else head[:MAX_SLUG_LENGTH]
    return slug or FALLBACK_SLUG


def make_branch_name(number: int, title: str) -> str:
    """`agent/<번호>-<slug>`를 반환한다. 번호가 0 이하이면 ValueError."""
    if number <= 0:
        raise ValueError(f"이슈 번호는 1 이상이어야 합니다: {number}")
    return f"agent/{number}-{_slugify(title)}"
