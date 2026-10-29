"""PreToolUse 훅: PLAN.md "절대 하지 말 것"을 강제한다.

stdin으로 훅 입력 JSON을 받아, 막아야 하면 permissionDecision "deny"를 출력한다.
입력을 읽지 못하면 exit 2로 차단한다 (fail closed).
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import PurePath

PREFIX = "[harness-guard] "
PROTECTED_BRANCHES = {"main", "master"}
SECRET_NAMES = {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"}
SECRET_SUFFIXES = {".pem", ".key"}
SECRET_VAR = re.compile(r"\$(env:)?\{?\w*(KEY|TOKEN|SECRET|PASSWORD|PASSWD)\w*", re.I)
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
# 따옴표 속(python -c "open('.env')")까지 잡도록 토큰이 아니라 원문에서 경로 후보를 찾는다
PATH_CANDIDATE = re.compile(
    r"[\w./\\~-]*(\.env[\w.]*|\.(pem|key)\b|id_(rsa|ed25519|ecdsa|dsa)\b|\.ssh[/\\][\w.]*)"
)
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def check_path(path: str) -> str | None:
    """시크릿 파일 경로면 차단 이유를, 아니면 None을 돌려준다."""
    p = path.strip("'\"").replace("\\", "/")
    name = PurePath(p).name.lower()
    is_example = name.startswith(".env.example")
    if name == ".env" or (name.startswith(".env.") and not is_example):
        return "환경변수 파일(.env)은 시크릿이 들어 있어 읽거나 쓸 수 없습니다"
    if name in SECRET_NAMES or PurePath(name).suffix in SECRET_SUFFIXES:
        return "키 파일(.pem/.key/id_rsa)은 읽거나 쓸 수 없습니다"
    if "/.ssh/" in f"/{p}" or p.startswith("~/.ssh"):
        return "~/.ssh 는 읽거나 쓸 수 없습니다"
    return None


def _tokens(segment: str) -> list[str]:
    try:
        # posix=False: Windows 경로의 백슬래시를 escape로 먹지 않게
        return [t.strip("'\"") for t in shlex.split(segment, posix=False)]
    except ValueError:
        return segment.split()


def _push_targets(args: list[str], branch: str) -> list[str]:
    """git push 인자에서 push 대상 브랜치 이름들을 뽑는다."""
    positional, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in PUSH_OPTS_WITH_VALUE:
            skip = True
        elif not a.startswith("-"):
            positional.append(a)
    refspecs = positional[1:]  # 첫 번째는 remote
    if not refspecs:
        return [branch]
    targets = []
    for ref in refspecs:
        dst = ref.split(":")[-1].removeprefix("refs/heads/")
        targets.append(branch if dst == "HEAD" else dst)
    return targets


def _check_git(tokens: list[str], branch: str) -> str | None:
    if "--no-verify" in tokens:
        return "--no-verify 로 훅을 우회할 수 없습니다"
    if "push" not in tokens:
        return None
    args = tokens[tokens.index("push") + 1 :]
    if "--dry-run" in args or "-n" in args:
        return None
    if any(
        a in ("-f", "--force") or a.startswith(("--force-with-lease", "+"))
        for a in args
    ):
        return "force push 는 금지입니다"
    # 브랜치를 알 수 없으면(detached 등) 보호 브랜치로 간주
    if any(t in PROTECTED_BRANCHES or t == "" for t in _push_targets(args, branch)):
        return "main 직접 push 는 금지입니다. agent/<이슈번호>-<요약> 브랜치에서 PR로 올리세요"
    return None


def _check_gh(tokens: list[str], segment: str) -> str | None:
    sub = tokens[1:3]
    if sub == ["auth", "token"]:
        return "토큰을 출력할 수 없습니다"
    if sub == ["pr", "merge"]:
        return "자동 머지는 금지입니다. 머지는 사람이 합니다"
    if sub[:1] == ["secret"]:
        return "GitHub Secrets 는 사용자가 직접 등록합니다"
    if sub == ["repo", "edit"] or (
        sub[:1] == ["api"] and re.search(r"protection|rulesets", segment)
    ):
        return "저장소 설정·브랜치 보호는 사용자가 직접 변경합니다"
    return None


def check_command(command: str, branch: str) -> str | None:
    """셸 명령이 금지 대상이면 차단 이유를, 아니면 None을 돌려준다."""
    for segment in SEGMENT_SPLIT.split(command):
        tokens = _tokens(segment.strip())
        if not tokens:
            continue
        head = tokens[0].lower()
        if head == "git":
            reason = _check_git(tokens, branch)
        elif head == "gh":
            reason = _check_gh(tokens, segment)
        else:
            reason = None
        if reason is None and (head == "printenv" or tokens == ["env"]):
            reason = "환경변수 전체 출력은 시크릿 노출 위험이 있습니다"
        if reason is None and any(t.lower().startswith("env:") for t in tokens):
            reason = "환경변수 전체 출력은 시크릿 노출 위험이 있습니다"
        if reason is None and SECRET_VAR.search(segment):
            reason = "KEY/TOKEN/SECRET 환경변수 값을 출력할 수 없습니다"
        # 커밋 메시지 속 ".env" 글자는 파일 접근이 아니므로 제외
        if reason is None and tokens[:2] != ["git", "commit"]:
            candidates = (m.group(0) for m in PATH_CANDIDATE.finditer(segment))
            reason = next((r for c in candidates if (r := check_path(c))), None)
        if reason:
            return reason
    return None


def _current_branch(cwd: str | None) -> str:
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True
        )
        return out.stdout.strip()
    except OSError:
        return ""


def main() -> int:
    # Claude Code는 UTF-8로 주고받는데 Windows 기본은 cp949라 한글이 깨짐
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    try:
        payload = json.loads(sys.stdin.read())
        tool = payload.get("tool_name", "")
        tool_input = payload.get("tool_input") or {}
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"{PREFIX}훅 입력을 읽지 못해 차단합니다: {e}", file=sys.stderr)
        return 2

    if tool in ("Bash", "PowerShell"):
        reason = check_command(
            tool_input.get("command", ""), _current_branch(payload.get("cwd"))
        )
    else:
        path = (
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
        )
        reason = check_path(path) if path else None

    if reason:
        decision = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": PREFIX + reason,
        }
        print(json.dumps({"hookSpecificOutput": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
