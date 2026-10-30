"""PR 크기 제한에 셀 줄 수 계산."""

from typing import Any


def _counts(filename: str) -> bool:
    if not filename.endswith(".md"):
        return True
    return filename.startswith(".claude/") or filename.rsplit("/", 1)[-1] == "CLAUDE.md"


def _item_lines(item: Any) -> int:
    if not isinstance(item, dict):
        raise ValueError(f"항목이 객체가 아님: {item!r}")
    name = item.get("filename")
    if not isinstance(name, str):
        raise ValueError(f"filename이 문자열이 아님: {item!r}")
    nums = []
    for key in ("additions", "deletions"):
        v = item.get(key)
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f"{key}가 정수가 아님: {item!r}")
        nums.append(v)
    return sum(nums) if _counts(name) else 0


def count_lines(data: Any) -> int:
    """파일 목록(또는 페이지 배열의 배열)에서 센 줄 수(additions+deletions)를 합산한다."""
    if not isinstance(data, list):
        raise ValueError("최상위 값이 배열이 아님")
    total = 0
    for entry in data:
        if isinstance(entry, list):
            total += sum(_item_lines(item) for item in entry)
        else:
            total += _item_lines(entry)
    return total
