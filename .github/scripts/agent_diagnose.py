"""에이전트가 결과 없이 끝났을 때 '왜'를 로그에 남긴다 (HARNESS P4 실패 10 build, 후속 fix 실전 — 같은 실패 2회).

기본 로그에는 에이전트의 마지막 답변도, 무엇이 거부됐는지도 없다. show_full_output은 도구 결과 전체를
공개 로그에 남기므로 쓰지 않고, 마지막 답변과 거부된 도구의 대상(명령·파일 경로)만 출력한다.
사용: python agent_diagnose.py <execution_file> [gate-log.jsonl]
출력은 모델 출력이라 호출하는 워크플로가 ::stop-commands::로 감싼다.
"""

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def summarize(events: Any) -> list[str]:
    events = events if isinstance(events, list) else [events]
    results = [e for e in events if isinstance(e, dict) and e.get("type") == "result"]
    r = results[-1] if results else {}
    lines = [
        f"종료: {r.get('subtype')} is_error={r.get('is_error')} 턴={r.get('num_turns')}",
        f"마지막 답변:\n{str(r.get('result') or '(없음)')[:2000]}",
    ]
    denials = r.get("permission_denials")
    for d in denials if isinstance(denials, list) else []:
        if not isinstance(d, dict):
            continue
        raw = d.get("tool_input")
        inp: dict = raw if isinstance(raw, dict) else {}
        target = str(inp.get("command") or inp.get("file_path") or "")[:300]
        lines.append(f"거부된 도구: {d.get('tool_name')} {target}")
    return lines


def gate_failures(lines: Iterable[str]) -> list[str]:
    """게이트 에스컬레이션은 result에 안 남을 수 있다 → block·escalate 줄(검사 이름만 있음)."""
    kept = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("result") in ("block", "escalate"):
            kept.append(line)
    return kept


def main(argv: list[str]) -> int:
    if len(argv) > 1 and Path(argv[1]).is_file():
        print(
            "\n".join(
                gate_failures(Path(argv[1]).read_text(encoding="utf-8").splitlines())
            )
        )
    execution = Path(argv[0]) if argv else None
    if execution is None or not execution.is_file():
        print("실행 기록 없음")
        return 0
    try:
        print("\n".join(summarize(json.loads(execution.read_text(encoding="utf-8")))))
    # 예상 밖 형식이어도 진단 단계 자체는 실패하지 않는다
    except (ValueError, AttributeError) as e:
        print(f"실행 기록을 읽지 못함: {e!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
