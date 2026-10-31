"""gate-log.jsonl 요약 (Phase 5 관측). 반복되는 실패를 숫자로 보고 docs/LEARNING.md 환류 절차에 넣는다.

사용: python .claude/hooks/observe.py [로그 파일...]
  인자가 없으면 로컬 로그. CI 기록은 `gh run download <run> -n gate-log`로 받아 경로를 넘긴다.
"""

import json
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# 명령줄에 상태 폴더 경로가 나오지 않게 기본값은 여기 둔다 (guard는 셸에서 .claude/state 접근을 막음)
LOCAL_LOG = Path(__file__).resolve().parent.parent / "state" / "gate-log.jsonl"


def summarize(lines: Iterable[str]) -> dict[str, Any]:
    results: Counter[str] = Counter()
    checks: Counter[str] = Counter()
    escalated: set[str] = set()
    broken = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            broken += 1
            continue
        if not isinstance(entry, dict):
            broken += 1
            continue
        result = str(entry.get("result"))
        results[result] += 1
        if result in ("block", "escalate"):
            checks.update(entry.get("failures") or [])
        if result == "escalate":
            escalated.add(str(entry.get("session")))
    reviews = results["review-approved"] + results["review-rejected"]
    return {
        "results": dict(results),
        "checks": dict(checks),
        "escalated": sorted(escalated),
        "rejection_rate": results["review-rejected"] / reviews if reviews else None,
        "broken": broken,
    }


def _table(title: str, counts: dict[str, int]) -> list[str]:
    rows = [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    return [f"| {title} | 횟수 |", "|---|---|", *(rows or ["| (없음) | 0 |"]), ""]


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or [LOCAL_LOG]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        print(f"로그 파일 없음: {', '.join(missing)}", file=sys.stderr)
        return 1
    lines = [ln for p in paths for ln in p.read_text(encoding="utf-8").splitlines()]
    s = summarize(lines)
    rate = s["rejection_rate"]
    out = [
        *_table("결과", s["results"]),
        *_table("block·escalate된 검사", s["checks"]),
        f"- 리뷰 거절률: {'-' if rate is None else f'{rate:.0%}'}",
        f"- 에스컬레이션 세션: {', '.join(s['escalated']) or '없음'}",
        f"- 읽지 못한 줄: {s['broken']}",
    ]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows 기본 cp949 (HARNESS Phase 1 실패 1)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
