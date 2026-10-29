"""guard.py 차단/허용 케이스. 실행: python -m pytest .claude/hooks/test_guard.py -v"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from guard import check_command, check_path  # noqa: E402

GUARD = Path(__file__).parent / "guard.py"

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
