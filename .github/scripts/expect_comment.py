"""에이전트 단계 뒤 '결과 확인': 새 댓글이 실제로 달렸는지 본다. 없으면 exit 1 → 워크플로의 실패 알림.

claude-code-action은 결과물 없이도 success로 끝날 수 있다 (HARNESS Phase 4 실패 5·10).
입력: stdin의 REST 댓글 배열 (`gh api --paginate .../comments | jq -s add`). 토큰은 다루지 않는다.
"""

import argparse
import json
import sys


def found(comments: list[dict], after_id: int, author: str, prefix: str) -> bool:
    """after_id보다 뒤(id는 단조 증가 — 러너 시계에 의존하지 않음)에 author가 prefix로 시작하는 댓글을 썼는가."""
    return any(
        c.get("id", 0) > after_id
        and (c.get("user") or {}).get("login") == author
        and (c.get("body") or "").startswith(prefix)
        for c in comments
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--after-id", type=int, required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--prefix", default="")
    args = p.parse_args(argv)
    if found(json.load(sys.stdin) or [], args.after_id, args.author, args.prefix):
        return 0
    print(
        f"결과 없음: 에이전트는 끝났지만 id {args.after_id} 이후 {args.author}의 '{args.prefix}' 댓글이 없다"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
