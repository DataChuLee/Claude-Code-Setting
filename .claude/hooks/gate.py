"""검증 게이트 훅. 재시도 횟수를 모델의 말이 아니라 파일(.claude/state/gate.json)로 센다.

모드 (settings.json에서 첫 인자로 지정):
  stop        Stop: 바뀐 .py가 있으면 pytest·ruff·mypy·TODO 검사. 실패 시 2회까지 되돌려 보내고 3번째에 멈춤
  reset       UserPromptExpansion(/gate-reset): 사람이 직접 입력했을 때만 재시도 횟수 초기화
  post-edit   PostToolUse(Edit|Write): 저장한 .py에 ruff만 빠르게, 실패 시 exit 2로 Claude에게 전달
  review-done PostToolUse(SubagentHandback)·SubagentStop(reviewer): reviewer 보고서가 "승인"이면 그 시점의 변경 해시 기록 → guard가 커밋 전에 대조
"""

import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

MAX_RETRIES = 2
PY = sys.executable
# 모든 검사를 합친 제한. Stop 훅 timeout(300초)보다 짧아야 훅이 강제 종료되기 전에 실패로 셀 수 있다
DEADLINE_SECONDS = 270


def _reviewable(name: str) -> bool:
    """리뷰 대상: 코드, 게이트 자체를 끌 수 있는 하네스 설정, 권한을 쥔 CI 워크플로 (상태 파일 제외)."""
    if name.startswith(".claude/state/"):
        return False
    return (
        name.endswith(".py")
        or name.startswith((".claude/", ".github/workflows/"))
        or name == "pyproject.toml"
    )


def _state_dir(root: Path) -> Path:
    path = root / ".claude" / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _git_lines(root: Path, *args: str) -> list[str] | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.splitlines() if result.returncode == 0 else None


def changed_files(root: Path) -> list[str]:
    """마지막 커밋 대비 바뀐 파일 + 새 파일 (스테이징 여부 무관, git 경로 표기)."""
    tracked = _git_lines(root, "diff", "HEAD", "--name-only")
    if tracked is None:  # 커밋이 아직 없는 저장소
        tracked = _git_lines(root, "ls-files") or []
    untracked = _git_lines(root, "ls-files", "--others", "--exclude-standard") or []
    return sorted(set(tracked + untracked))


def change_hash(root: Path) -> str:
    """바뀐 리뷰 대상 파일의 경로와 내용으로 만든 해시. 같은 코드면 같은 값."""
    digest = hashlib.sha256()
    for name in (f for f in changed_files(root) if _reviewable(f)):
        path = root / name
        content = path.read_bytes() if path.exists() else b"<deleted>"
        digest.update(f"{name}\0{len(content)}\0".encode() + content)
    return digest.hexdigest()


def _tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _todo_failures(files: list[str]) -> list[tuple[str, str]]:
    features = {
        "/".join(PurePosixPath(f).parts[:2])
        for f in files
        if f.endswith(".py")
        and f.startswith("src/")
        and len(PurePosixPath(f).parts) >= 3
    }
    return [
        ("todo", f"{feat}/ 코드가 바뀌었는데 {feat}/TODO.md 가 갱신되지 않았습니다")
        for feat in sorted(features)
        if f"{feat}/TODO.md" not in files
    ]


def mypy_targets(root: Path, files: list[str]) -> list[str]:
    """코드 폴더 전부 + 그 밖(루트 등)에서 바뀐 .py. 리뷰에서 루트 파일이 타입 검사 밖이던 구멍 발견."""
    dirs = ("src", "tests", ".claude/hooks")
    targets = [d for d in dirs if (root / d).is_dir()]
    outside = [
        f
        for f in files
        if f.endswith(".py")
        and not f.startswith(tuple(d + "/" for d in dirs))
        and (root / f).exists()
    ]
    return targets + outside


def run_checks(root: Path, files: list[str]) -> list[tuple[str, str]]:
    """실패한 검사의 (이름, 출력 끝부분) 목록. 도구 실행 자체가 안 되면 실패로 본다."""
    checks = [
        ("pytest", [PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"]),
        ("ruff check", [PY, "-m", "ruff", "check", "."]),
        ("ruff format", [PY, "-m", "ruff", "format", "--check", "."]),
    ]
    targets = mypy_targets(root, files)
    if targets:
        checks.append(("mypy", [PY, "-m", "mypy", *targets]))

    failures = []
    deadline = time.monotonic() + DEADLINE_SECONDS
    for name, cmd in checks:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            failures.append(
                (name, "시간 초과: 앞선 검사가 제한 시간을 다 써서 실행하지 못함")
            )
            continue
        try:
            result = subprocess.run(
                cmd,
                cwd=root,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=remaining,
            )
        except subprocess.TimeoutExpired:
            failures.append(
                (
                    name,
                    f"시간 초과: {DEADLINE_SECONDS}초 안에 끝나지 않음 (멈춘 테스트?)",
                )
            )
            continue
        except OSError as e:
            failures.append((name, f"실행 실패: {e}"))
            continue
        no_tests = name == "pytest" and result.returncode == 5
        if result.returncode != 0 and not no_tests:
            failures.append((name, _tail(result.stdout + result.stderr)))
    return failures + _todo_failures(files)


def load_state(root: Path) -> dict:
    path = _state_dir(root) / "gate.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _save_state(root: Path, state: dict) -> None:
    (_state_dir(root) / "gate.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def _log(root: Path, **entry: object) -> None:
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(_state_dir(root) / "gate-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def stop(payload: dict, root: Path) -> dict | None:
    """Stop 훅 응답(JSON). None이면 그대로 멈춰도 됨."""
    session = str(payload.get("session_id", "unknown"))
    files = changed_files(root)
    if not any(f.endswith(".py") for f in files):
        return None
    state = load_state(root)
    entry = state.setdefault(session, {"attempts": 0, "passed_hash": None})
    current = change_hash(root)
    if entry["passed_hash"] == current:
        return None

    failures = run_checks(root, files)
    names = [name for name, _ in failures]
    if not failures:
        entry.update(attempts=0, passed_hash=current)
        _save_state(root, state)
        _log(root, session=session, result="pass")
        return None

    entry["attempts"] += 1
    _save_state(root, state)
    attempts = entry["attempts"]
    if attempts <= MAX_RETRIES:
        _log(root, session=session, result="block", attempts=attempts, failures=names)
        detail = "\n\n".join(f"## {name}\n{out}" for name, out in failures)
        reason = f"[gate] 검증 실패 — 재시도 {attempts}/{MAX_RETRIES}. 고친 뒤 다시 끝내세요.\n\n{detail}"
        return {"decision": "block", "reason": reason}

    _log(root, session=session, result="escalate", attempts=attempts, failures=names)
    return {
        "continue": False,
        "stopReason": (
            f"[gate] 재시도 {MAX_RETRIES}회를 넘겨 멈춥니다 — 사람 확인 필요 (실패: {', '.join(names)}). "
            "확인 후 /gate-reset 으로 재시도 횟수를 초기화하세요."
        ),
    }


def reset(payload: dict, root: Path) -> None:
    state = load_state(root)
    state.setdefault(str(payload.get("session_id", "unknown")), {"passed_hash": None})[
        "attempts"
    ] = 0
    _save_state(root, state)
    _log(root, session=payload.get("session_id"), result="reset")


def _approved(report: str) -> bool:
    """reviewer 출력의 마지막 '승인 가능 여부:' 줄이 '✅ 승인'으로 시작하고 ❌가 없을 때만 승인."""
    verdicts = [
        line.split(":", 1)[1]
        for line in report.splitlines()
        if line.strip().lstrip("#*- ").startswith("승인 가능 여부") and ":" in line
    ]
    if not verdicts:
        return False
    # 정확한 승인 형식만 인정 ("승인 불가"·"미승인"도 '승인' 글자를 포함하므로 포함 여부로 보면 안 됨)
    last = verdicts[-1].strip(" *")
    return last.startswith("✅ 승인") and "❌" not in last


def review_done(payload: dict, root: Path) -> None:
    """reviewer의 보고서로 리뷰 기록. 보고서는 auto 모드면 SubagentHandback의 tool_input.message,
    그 외(CI의 -p)면 SubagentStop의 last_assistant_message로 온다. Handback 뒤의 SubagentStop은
    맺음말뿐일 수 있다(공식 문서) → 빈 보고서와 판정 줄 없는 SubagentStop은 무시."""
    if payload.get("agent_type") != "reviewer":
        return
    summary = str(
        (payload.get("tool_input") or {}).get("message")
        or payload.get("last_assistant_message")
        or ""
    )
    if not summary.strip():
        return
    # auto 모드에서는 Handback 뒤 SubagentStop이 맺음말만 들고 온다 → 판정 줄이 없으면 앞 기록 유지
    # (CI처럼 Handback이 없으면 SubagentStop의 마지막 텍스트가 보고서 자체다)
    if (
        payload.get("hook_event_name") == "SubagentStop"
        and "승인 가능 여부" not in summary
    ):
        return
    rejected = not _approved(summary)
    record = {
        "hash": None if rejected else change_hash(root),
        "rejected": rejected,
        "agent_type": payload.get("agent_type"),
        "summary": summary[:4000],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (_state_dir(root) / "review.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # review.json은 마지막 리뷰만 남으므로, 라운드별 지적은 로그에 쌓아 PR 본문(ship)에 쓴다
    _log(
        root,
        result="review-rejected" if rejected else "review-approved",
        summary=record["summary"],
    )


def review_matches(root: Path) -> bool:
    """리뷰 대상 변경이 없거나, 마지막 승인 리뷰가 지금 코드와 같으면 True."""
    if not any(_reviewable(f) for f in changed_files(root)):
        return True
    try:
        record = json.loads(
            (root / ".claude" / "state" / "review.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return record.get("hash") == change_hash(root)


def _post_edit(payload: dict) -> int:
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not path.endswith(".py") or not Path(path).exists():
        return 0
    result = subprocess.run(
        [PY, "-m", "ruff", "check", path],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(
            f"[gate] ruff 오류 — 바로 고치세요:\n{_tail(result.stdout + result.stderr)}",
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = json.loads(sys.stdin.read() or "{}")
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")

    if mode == "post-edit":
        return _post_edit(payload)
    if mode == "stop":
        output = stop(payload, root)
        if output:
            print(json.dumps(output, ensure_ascii=False))
    elif mode == "reset" and payload.get("command_name") == "gate-reset":
        reset(payload, root)
    elif mode == "review-done":
        review_done(payload, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
