"""PreToolUse 훅 진입점. guard.py로 판정하고, guard가 고장 나면 guard 수정만 허용한다.

판정 규칙은 guard.py에 두고, 이 파일은 작게 유지하며 거의 바꾸지 않는다.
(guard.py를 고치다 깨뜨리면 모든 도구가 막혀 guard를 고칠 수도 없게 된 사고 이후 분리)
"""

import io
import json
import os
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
PREFIX = "[harness-guard] "


def _deny(reason: str) -> None:
    decision = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": PREFIX + reason,
    }
    print(json.dumps({"hookSpecificOutput": decision}, ensure_ascii=False))


def _is_guard_repair(payload: dict) -> bool:
    path = (payload.get("tool_input") or {}).get("file_path")
    if payload.get("tool_name") not in ("Edit", "Write") or not isinstance(path, str):
        return False
    target = os.path.normcase(Path(path).resolve())
    return target == os.path.normcase(HOOKS / "guard.py")


def main() -> int:
    # Claude Code는 UTF-8로 주고받는데 Windows 기본은 cp949라 한글이 깨짐
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("JSON 객체가 아님")
    except ValueError as e:
        print(f"{PREFIX}훅 입력을 읽지 못해 차단합니다: {e}", file=sys.stderr)
        return 2

    try:
        sys.path.insert(0, str(HOOKS))
        import guard

        reason = guard.decide(payload)
    except Exception as e:  # guard 고장: 차단하되 guard 자체를 고치는 길은 열어 둔다
        if _is_guard_repair(payload):
            return 0
        reason = f"guard.py 고장({type(e).__name__}: {e}). guard.py 수정(Edit/Write)만 허용됩니다"

    if reason:
        _deny(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
