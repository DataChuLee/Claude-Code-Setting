"""봇이 쓴 SPEC 댓글은 소유자의 👍(+1) 반응이 있어야 승인된 것으로 본다.

GITHUB_TOKEN으로는 소유자 이름의 반응을 만들 수 없다 → 주입된 이전 실행이 봇 이름으로 가짜 SPEC을 달아도 승인되지 않는다.
반응은 댓글의 updated_at을 바꾸지 않는다(2026-10-31 이슈 #11에서 확인) → 기존 "수정된 봇 SPEC 거부" 검사와 함께 쓸 수 있다.
입력: stdin의 REST 반응 배열 (`gh api --paginate .../issues/comments/<id>/reactions | jq -s add`).
"""

import argparse
import json
import sys


def approved(reactions: list[dict], owner: str) -> bool:
    return any(
        (r.get("user") or {}).get("login") == owner and r.get("content") == "+1"
        for r in reactions
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--owner", required=True)
    args = p.parse_args(argv)
    if approved(json.load(sys.stdin) or [], args.owner):
        return 0
    print(
        f"봇이 쓴 SPEC에 소유자({args.owner})의 👍가 없습니다. SPEC 댓글에 👍를 단 뒤 agent:build 라벨을 다시 붙이세요"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
