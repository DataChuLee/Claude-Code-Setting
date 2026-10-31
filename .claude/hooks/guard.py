"""PLAN.md "절대 하지 말 것" 판정 규칙. 훅 진입점(입출력·고장 처리)은 run_guard.py.

decide(payload)가 차단 이유를 돌려주면 run_guard.py가 deny로 응답한다.
"""

import re
import shlex
import subprocess
import sys
from pathlib import Path, PurePath

PROTECTED_BRANCHES = {"main", "master"}
SECRET_NAMES = {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"}
SECRET_SUFFIXES = {".pem", ".key"}
SECRET_VAR = re.compile(r"\$(env:)?\{?\w*(KEY|TOKEN|SECRET|PASSWORD|PASSWD)\w*", re.I)
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
# 따옴표 속(python -c "open('.env')")까지 잡도록 토큰이 아니라 원문에서 경로 후보를 찾는다
PATH_CANDIDATE = re.compile(
    r"[\w./\\~-]*(\.env[\w.]*|\.(pem|key)\b|id_(rsa|ed25519|ecdsa|dsa)\b|\.ssh[/\\][\w.]*)"
)
REDIRECT = re.compile(r"(\d+|&)?(>>?|<)(&\d)?")  # 2>&1, >, 2>err.txt, &>x 의 앞부분
# 연산자만 있는 토큰: 다음 토큰이 파일 이름.
# `*>`(PowerShell)는 인정하지 않는다: bash에서는 glob `*`가 파일 이름(예: main)으로 펼쳐져 push 인자가 된다
REDIRECT_OP = re.compile(r"(\d+|&)?(>>?|<)")
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


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


def _tokens(segment: str, drop_redirects: bool = False) -> list[str]:
    try:
        # posix=False: Windows 경로의 백슬래시를 escape로 먹지 않게
        raw = shlex.split(segment, posix=False)
    except ValueError:
        raw = segment.split()
    if drop_redirects:
        # 따옴표를 벗기기 전에 판정: '">"'처럼 따옴표 속 기호는 리다이렉트가 아니라 진짜 인자
        kept, skip_file = [], False
        for t in raw:
            if skip_file:
                skip_file = False
            elif REDIRECT_OP.fullmatch(t):
                skip_file = True
            elif not REDIRECT.match(t):
                kept.append(t)
        raw = kept
    return [t.strip("'\"") for t in raw]


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


def _program(tokens: list[str]) -> tuple[str, list[str]]:
    """git/gh를 경로(git.exe, C:\\...\\gh.exe)나 접두어(env, sudo, &) 뒤에서도 찾는다."""
    for i, t in enumerate(tokens):
        name = PurePath(t.replace("\\", "/")).name.lower().removesuffix(".exe")
        if name in ("git", "gh"):
            return name, [name, *tokens[i + 1 :]]
    return tokens[0].lower(), tokens


def _git_subcommand(tokens: list[str]) -> int | None:
    """git 전역 옵션(-C 경로 등)을 건너뛰고 하위 명령의 위치를 돌려준다."""
    skip = False
    for i, t in enumerate(tokens[1:], start=1):
        if skip:
            skip = False
        elif t in GIT_OPTS_WITH_VALUE:
            skip = True
        elif not t.startswith("-"):
            return i
    return None


def _check_git(tokens: list[str], branch: str) -> str | None:
    if "--no-verify" in tokens:
        return "--no-verify 로 훅을 우회할 수 없습니다"
    sub = _git_subcommand(tokens)
    lowered = [t.lower() for t in tokens]
    config_env = any(t.startswith("--config-env") for t in lowered)
    sets_alias = any(t.startswith("alias.") for t in lowered) and (
        "-c" in tokens or (sub is not None and tokens[sub] == "config")
    )
    if config_env or sets_alias:
        return "git alias 정의(-c alias.*, config alias.*, --config-env)로 검사를 피할 수 없습니다"
    if sub is None or tokens[sub] != "push":
        return None
    args = tokens[sub + 1 :]
    if "--dry-run" in args or "-n" in args:
        return None
    if any(
        a in ("-f", "--force") or a.startswith(("--force-with-lease", "+"))
        for a in args
    ):
        return "force push 는 금지입니다"
    # 브랜치를 알 수 없으면(detached 등) 보호 브랜치로 간주
    if {"--all", "--mirror", "--branches"} & set(args):
        return "모든 브랜치 push(--all/--mirror/--branches)는 금지입니다. agent/ 브랜치 하나만 push 하세요"
    targets = _push_targets(args, branch)
    if any(t in PROTECTED_BRANCHES or t == "" for t in targets):
        return "main 직접 push 는 금지입니다. agent/<이슈번호>-<요약> 브랜치에서 PR로 올리세요"
    if any(not t.startswith("agent/") for t in targets):
        return "push 는 agent/<이슈번호>-<요약> 브랜치에만 할 수 있습니다"
    return None


# gh api로 머지·ready 전환·자동 머지·머지 큐 (REST PUT pulls/N/merge, GraphQL mutation 이름)
GH_API_MERGE_OR_READY = re.compile(
    r"pulls/[^/\s]+/merge\b|markPullRequestReadyForReview|mergePullRequest"
    r"|enablePullRequestAutoMerge|enqueuePullRequest",
    re.I,
)
SHELL_QUOTES = re.compile(r"[\"'`\\]")  # 셸은 벗겨 이어 붙인다: mer''ge → merge


def _gh_sub(tokens: list[str]) -> list[str]:
    """gh 하위 명령 두 단어. 그 앞에 끼운 플래그는 건너뛴다 (gh pr -R o/r merge 1).

    하위 명령 이름은 '-'로 시작하지 않는다. 값을 따로 받는 플래그는 -R/--repo뿐이다.
    """
    sub: list[str] = []
    i = 1
    while i < len(tokens) and len(sub) < 2:
        t = tokens[i]
        if t in ("-R", "--repo"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        sub.append(t)
        i += 1
    return sub


def _check_gh(tokens: list[str], segment: str) -> str | None:
    sub = _gh_sub(tokens)
    if sub == ["auth", "token"]:
        return "토큰을 출력할 수 없습니다"
    if sub in (["pr", "merge"], ["pr", "ready"]) or (
        sub[:1] == ["api"]
        and GH_API_MERGE_OR_READY.search(SHELL_QUOTES.sub("", segment))
    ):
        return "머지와 ready 전환은 사람이 합니다"
    # set·import·delete 모두 정의를 바꾼다. ls는 list의 공식 별칭
    if sub[:1] == ["alias"] and sub[1:2] not in (["list"], ["ls"]):
        return "gh alias 정의로 검사를 피할 수 없습니다"
    is_create = sub in (["pr", "create"], ["pr", "new"])  # new는 create의 공식 별칭
    if is_create and (
        not {"--draft", "-d"} & set(tokens)
        or any(t.startswith(("--draft=", "-d=")) for t in tokens)
    ):
        return "PR 은 draft 로만 만듭니다 (--draft). ready 전환과 머지는 사람이 합니다"
    if sub[:1] == ["secret"]:
        return "GitHub Secrets 는 사용자가 직접 등록합니다"
    if sub == ["repo", "edit"] or (
        sub[:1] == ["api"] and re.search(r"protection|rulesets", segment)
    ):
        return "저장소 설정·브랜치 보호는 사용자가 직접 변경합니다"
    return None


SHELLS = {"bash", "sh", "zsh", "pwsh", "powershell", "cmd"}
SHELL_FLAGS = {"-c", "-command", "/c"}
HARNESS_STATE = re.compile(r"\.claude[/\\]state\b", re.I)  # NTFS는 대소문자 무시
GATE_PRIVATE_MODE = re.compile(r"gate\.py\W+(review-done|reset)\b")
COMMIT_LIKE = {
    "commit",
    "merge",
    "cherry-pick",
    "revert",
    "am",
}  # pull·rebase는 소음이 커서 제외
READ_TOOLS = {"Read", "Grep", "Glob"}


def _nested_commands(tokens: list[str]) -> list[str]:
    """bash -c "..." · pwsh -Command "..." 안의 명령 (따옴표로 묶여 검사를 피하던 구멍)."""
    name = PurePath(tokens[0].replace("\\", "/")).name.lower().removesuffix(".exe")
    if name not in SHELLS:
        return []
    # -c 뿐 아니라 -lc·-ec처럼 붙여 쓴 플래그도
    return [
        tokens[i + 1]
        for i, t in enumerate(tokens[:-1])
        if t.lower() in SHELL_FLAGS or re.fullmatch(r"-[a-z]*c", t.lower())
    ]


def _harness_reason(segment: str) -> str | None:
    """게이트 상태·전용 모드는 훅만 다룬다 (모델이 리뷰 기록을 위조하거나 카운터를 초기화하지 못하게)."""
    if HARNESS_STATE.search(segment):
        return "하네스 상태(.claude/state)는 훅만 씁니다. 읽기는 Read 도구로"
    if GATE_PRIVATE_MODE.search(segment):
        return "gate.py review-done/reset 은 훅 전용입니다 (리뷰는 reviewer 에이전트, 초기화는 사람이 /gate-reset)"
    return None


def check_command(command: str, branch: str) -> str | None:
    """셸 명령이 금지 대상이면 차단 이유를, 아니면 None을 돌려준다."""
    for segment in SEGMENT_SPLIT.split(command):
        tokens = _tokens(segment.strip())
        if not tokens:
            continue
        for nested in _nested_commands(tokens):
            if nested_reason := check_command(nested, branch):
                return nested_reason
        if harness_reason := _harness_reason(segment):
            return harness_reason
        head, program_tokens = _program(tokens)
        if head == "git":
            reason = _check_git(
                _program(_tokens(segment.strip(), drop_redirects=True))[1], branch
            )
        elif head == "gh":
            # api 본문(GraphQL 쿼리)은 여러 줄일 수 있는데 segment는 줄 단위로 잘린다 → 명령 전체를 본다
            reason = _check_gh(program_tokens, command)
        else:
            reason = None
        if reason is None and (head == "printenv" or tokens == ["env"]):
            reason = "환경변수 전체 출력은 시크릿 노출 위험이 있습니다"
        if reason is None and any(t.lower().startswith("env:") for t in tokens):
            reason = "환경변수 전체 출력은 시크릿 노출 위험이 있습니다"
        if reason is None and SECRET_VAR.search(segment):
            reason = "KEY/TOKEN/SECRET 환경변수 값을 출력할 수 없습니다"
        # 커밋 메시지 속 ".env" 글자는 파일 접근이 아니므로 제외
        if reason is None and program_tokens[:2] != ["git", "commit"]:
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


def _native_path(path: str) -> str:
    """Git Bash 표기(/c/Users/..)를 Windows 경로(C:/Users/..)로."""
    match = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    if sys.platform == "win32" and match:
        return f"{match.group(1).upper()}:{match.group(2) or '/'}"
    return path


def _commit_dirs(command: str, cwd: str | None) -> list[Path]:
    """명령이 커밋하는 저장소 위치들. 앞선 cd 와 git -C 를 따라간다."""
    here = Path(cwd or ".")
    dirs = []
    for segment in SEGMENT_SPLIT.split(command):
        tokens = _tokens(segment.strip())
        if not tokens:
            continue
        if tokens[0].lower() in ("cd", "set-location", "pushd") and len(tokens) > 1:
            here = here / _native_path(tokens[1])  # 절대 경로면 그대로 바뀜
            continue
        for nested in _nested_commands(tokens):
            dirs.extend(_commit_dirs(nested, str(here)))
        head, program_tokens = _program(tokens)
        sub = _git_subcommand(program_tokens) if head == "git" else None
        if sub is None or program_tokens[sub] not in COMMIT_LIKE:
            continue
        target = here
        for i in range(1, sub):
            if program_tokens[i] == "-C" and i + 1 < sub:
                target = target / _native_path(program_tokens[i + 1])
        dirs.append(target)
    return dirs


def _review_reason(repo_dir: Path) -> str | None:
    """커밋 전 리뷰 필수: reviewer가 본 코드와 지금 코드가 같아야 한다."""
    import gate  # 같은 폴더. 해시 계산을 게이트와 공유

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except OSError:
        top = ""  # 확인할 수 없으면 차단
    if top and gate.review_matches(Path(top)):
        return None
    return "커밋 전에 reviewer 에이전트로 현재 변경을 검토하세요 (리뷰 후 코드가 바뀌었으면 다시 검토)"


def _commit_review_reason(command: str, cwd: str | None) -> str | None:
    return next(
        (r for d in _commit_dirs(command, cwd) if (r := _review_reason(d))), None
    )


def decide(payload: dict) -> str | None:
    """훅 입력 하나를 판정한다. 도구 이름이 아니라 입력 형태로 본다 (matcher "*").

    command가 있으면 셸 명령(Bash·PowerShell·Monitor 등), 경로가 있으면 파일 접근으로 검사.
    """
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if isinstance(command, str):
        cwd = payload.get("cwd")
        reason = check_command(command, _current_branch(cwd))
        return reason or _commit_review_reason(command, cwd)
    path = (
        tool_input.get("file_path")
        or tool_input.get("notebook_path")
        or tool_input.get("path")
    )
    if not isinstance(path, str):
        return None
    # hooks/../state 같은 우회를 막으려고 정규화한 경로로 검사
    if HARNESS_STATE.search(str(Path(path).resolve())) and (
        payload.get("tool_name") not in READ_TOOLS
    ):
        return "하네스 상태(.claude/state)는 훅만 씁니다"
    return check_path(path)
