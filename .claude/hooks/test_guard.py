"""guard.py 차단/허용 케이스. 실행: python -m pytest .claude/hooks/test_guard.py -v"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import gate  # noqa: E402
from guard import check_command, check_path, decide  # noqa: E402

HOOKS = Path(__file__).parent
GUARD = HOOKS / "run_guard.py"  # 훅 진입점 (guard.py를 불러 판정)

BLOCKED = [
    # main 직접 push
    ("git push origin main", "feature"),
    ("git push origin HEAD:main", "feature"),
    ("git push origin master", "feature"),
    ("git -C . push origin main", "feature"),
    ("git push", "main"),
    ("git push origin", "main"),
    ("git push -u origin HEAD", "main"),
    ("cd repo && git push origin main", "feature"),
    # force push
    ("git push --force origin agent/1-x", "agent/1-x"),
    ("git push -f origin agent/1-x", "agent/1-x"),
    ("git push origin +agent/1-x", "agent/1-x"),
    ("git push --force-with-lease origin main", "feature"),
    # 훅 우회
    ("git commit --no-verify -m x", "feature"),
    # 시크릿 읽기·출력
    ("cat .env", "feature"),
    ("cat ./config/.env.local", "feature"),
    ("type .env", "feature"),
    ("Get-Content .env", "feature"),
    ("gc .env", "feature"),
    ("head -n 3 server.pem", "feature"),
    ("cat ~/.ssh/id_rsa", "feature"),
    ("gh auth token", "feature"),
    ("printenv", "feature"),
    ("printenv OPENAI_API_KEY", "feature"),
    ("env", "feature"),
    ("echo $OPENAI_API_KEY", "feature"),
    ("echo $env:OPENAI_API_KEY", "feature"),
    ("Get-ChildItem env:", "feature"),
    # 실행 파일 경로·접두어로 우회
    ("git.exe push origin main", "feature"),
    ('& "C:\\Program Files\\Git\\bin\\git.exe" push origin main', "feature"),
    ('"/c/Program Files/GitHub CLI/gh.exe" pr merge 1', "feature"),
    ("env FOO=1 git push origin main", "feature"),
    ("sudo git push --force origin agent/1-x", "agent/1-x"),
    # 셸 안의 셸, alias, 하네스 상태 조작 (Phase 2 리뷰 지적)
    ('bash -c "git push origin main"', "feature"),
    ("pwsh -Command 'gh pr merge 1'", "feature"),
    ("git -c alias.ci=commit ci -m x", "feature"),
    ("python .claude/hooks/gate.py review-done", "feature"),
    ("python .claude/hooks/gate.py reset", "feature"),
    ("echo {} > .claude/state/review.json", "feature"),
    ("echo {} > .CLAUDE/STATE/review.json", "feature"),
    ('bash -lc "git push origin main"', "feature"),
    ('sh -ec "gh pr merge 1"', "feature"),
    ("git config alias.ci commit", "feature"),
    ("git --config-env=alias.ci=V ci", "feature"),
    # 인터프리터로 우회 (따옴표 속 경로)
    ("python -c \"print(open('.env').read())\"", "feature"),
    ("python -c \"open('keys/server.pem').read()\"", "feature"),
    ("node -e \"require('fs').readFileSync('.env.local')\"", "feature"),
    # 저장소 설정 변경
    ("gh api -X PUT repos/o/r/branches/main/protection", "feature"),
    ("gh repo edit --default-branch dev", "feature"),
    ("gh secret set OPENAI_API_KEY", "feature"),
    # 자동 머지
    ("gh pr merge 3 --squash", "feature"),
]

ALLOWED = [
    ("git push origin agent/12-foo", "agent/12-foo"),
    ("git push -u origin agent/12-foo", "agent/12-foo"),
    ("git push", "agent/12-foo"),
    ("git push --dry-run origin agent/0-test", "main"),
    ("git status", "main"),
    ("git stash push -m wip", "main"),
    ("git -C sub log --oneline", "main"),
    ('"/c/Program Files/GitHub CLI/gh.exe" pr view 1', "main"),
    ("git commit -m 'fix env loading'", "feature"),
    ("git commit -m 'chore: ignore .env'", "feature"),
    ("cat README.md", "main"),
    ("cat .env.example", "main"),
    ("echo hello", "main"),
    ("python -m pytest", "main"),
    ("gh pr create --draft --title x", "agent/1-x"),
    ("gh pr view 3", "feature"),
    ("env FOO=1 python app.py", "feature"),
    ("python -c \"print('hello')\"", "feature"),
    ("pip install python-dotenv", "feature"),
    ('python -c "d={}; print(d.keys())"', "feature"),
    ("cp .env.example .env.example.bak", "feature"),
]


@pytest.mark.parametrize("command,branch", BLOCKED)
def test_dangerous_command_is_blocked(command, branch):
    assert check_command(command, branch) is not None


@pytest.mark.parametrize("command,branch", ALLOWED)
def test_safe_command_is_allowed(command, branch):
    assert check_command(command, branch) is None


@pytest.mark.parametrize(
    "path",
    [".env", "C:\\proj\\.env", "/proj/.env.production", "keys/server.pem", "id_rsa"],
)
def test_secret_path_is_blocked(path):
    assert check_path(path) is not None


@pytest.mark.parametrize(
    "path", [".env.example", "src/env.py", "README.md", "docs/PLAN.md"]
)
def test_normal_path_is_allowed(path):
    assert check_path(path) is None


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    # Claude Code처럼 UTF-8로 주고받는다 (Windows 기본 cp949와 다름)
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        encoding="utf-8",
    )


def test_hook_reason_is_utf8_korean():
    result = _run_hook({"tool_name": "Bash", "tool_input": {"command": "cat .env"}})
    reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "환경변수" in reason


def test_hook_reads_korean_command():
    command = "git commit -m '기능 추가' --no-verify"
    result = _run_hook({"tool_name": "Bash", "tool_input": {"command": command}})
    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


def test_hook_denies_via_json_on_stdin():
    result = _run_hook(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}}
    )
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert result.returncode == 0
    assert out["permissionDecision"] == "deny"
    assert out["permissionDecisionReason"].startswith("[harness-guard]")


def test_hook_is_silent_for_safe_command():
    result = _run_hook(
        {"tool_name": "PowerShell", "tool_input": {"command": "git status"}}
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_hook_checks_file_tools():
    result = _run_hook(
        {"tool_name": "Read", "tool_input": {"file_path": "C:\\p\\.env"}}
    )
    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


def test_hook_blocks_on_unreadable_input():
    # 검사 불가 → 차단 (fail closed)
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input="not json",
        capture_output=True,
        encoding="utf-8",
    )
    assert result.returncode == 2


def _deny(result: subprocess.CompletedProcess) -> str | None:
    if not result.stdout:
        return None
    out = json.loads(result.stdout)["hookSpecificOutput"]
    return (
        out["permissionDecisionReason"] if out["permissionDecision"] == "deny" else None
    )


def test_any_tool_with_command_is_checked():
    # matcher "*": Monitor처럼 셸을 실행하는 도구도 command 필드로 검사
    result = _run_hook(
        {"tool_name": "Monitor", "tool_input": {"command": "gh pr merge 1"}}
    )
    assert _deny(result)


def test_tool_without_command_or_path_is_allowed():
    result = _run_hook({"tool_name": "WebSearch", "tool_input": {"query": "pytest"}})
    assert _deny(result) is None


def _broken_hooks(tmp_path: Path) -> Path:
    (tmp_path / "run_guard.py").write_text(
        GUARD.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "guard.py").write_text("def broken(:\n", encoding="utf-8")
    return tmp_path


def _run_broken(hooks: Path, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hooks / "run_guard.py")],
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
    )


def test_broken_guard_still_allows_repairing_guard(tmp_path):
    hooks = _broken_hooks(tmp_path)
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(hooks / "guard.py")},
    }
    assert _deny(_run_broken(hooks, payload)) is None


def test_broken_guard_blocks_everything_else(tmp_path):
    hooks = _broken_hooks(tmp_path)
    for payload in (
        {"tool_name": "Bash", "tool_input": {"command": "git status"}},
        {"tool_name": "Edit", "tool_input": {"file_path": str(hooks / "other.py")}},
    ):
        assert "고장" in (_deny(_run_broken(hooks, payload)) or "")


def _repo_with_change(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "app.py").write_text("X = 1\n")
    return tmp_path


def test_commit_without_review_is_blocked(tmp_path):
    repo = _repo_with_change(tmp_path)
    payload = {"tool_input": {"command": "git commit -m 'feat: x'"}, "cwd": str(repo)}
    assert "reviewer" in (decide(payload) or "")


def test_commit_after_review_of_same_code_is_allowed(tmp_path):
    repo = _repo_with_change(tmp_path)
    approve = {
        "agent_type": "reviewer",
        "tool_input": {"message": "승인 가능 여부: ✅ 승인"},
    }
    gate.review_done(approve, repo)
    payload = {"tool_input": {"command": "git commit -m 'feat: x'"}, "cwd": str(repo)}
    assert decide(payload) is None
    (repo / "app.py").write_text("X = 2\n")
    assert decide(payload)


def test_commit_review_checks_the_repo_actually_committed(tmp_path):
    changed = _repo_with_change(tmp_path / "changed")
    clean = tmp_path / "clean"
    clean.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=clean, check=True)
    for command in (
        f'git -C "{clean}" commit -m x',
        f'cd "{clean}" && git commit -m x',
    ):
        assert decide({"tool_input": {"command": command}, "cwd": str(changed)}) is None


def test_harness_state_cannot_be_written_but_can_be_read(tmp_path):
    state = str(tmp_path / ".claude" / "state" / "review.json")
    assert decide({"tool_name": "Write", "tool_input": {"file_path": state}})
    assert decide({"tool_name": "Edit", "tool_input": {"file_path": state}})
    assert decide({"tool_name": "Read", "tool_input": {"file_path": state}}) is None
    for disguised in (
        str(tmp_path / ".claude" / "hooks" / ".." / "state" / "review.json"),
        str(tmp_path / ".CLAUDE" / "STATE" / "review.json"),
    ):
        assert decide({"tool_name": "Write", "tool_input": {"file_path": disguised}})


def test_commit_inside_nested_shell_or_merge_needs_review(tmp_path):
    repo = _repo_with_change(tmp_path)
    for command in (
        'bash -c "git commit -m x"',
        'bash -lc "git commit -m x"',
        "git merge --no-ff topic",
    ):
        assert decide({"tool_input": {"command": command}, "cwd": str(repo)})


def test_git_bash_drive_path_is_converted():
    from guard import _native_path

    expected = "C:/Users/me" if sys.platform == "win32" else "/c/Users/me"
    assert _native_path("/c/Users/me") == expected
