"""gate.py 재시도 카운터·리뷰 해시·TODO 검사. 임시 git 저장소에서 실제 검사 도구를 돌린다."""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import gate  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def _stop(repo: Path) -> dict | None:
    return gate.stop({"session_id": "s1"}, repo)


def _break_tests(repo: Path) -> None:
    (repo / "tests" / "test_bad.py").write_text("def test_bad():\n    assert False\n")


@pytest.fixture
def fake_checks(monkeypatch):
    """카운터 로직만 볼 때는 실제 도구 대신 test_bad.py 내용으로 성패를 정한다 (게이트 속도)."""

    def run_checks(root, files):
        bad = root / "tests" / "test_bad.py"
        failing = bad.exists() and "False" in bad.read_text()
        return [("pytest", "assert False")] if failing else []

    monkeypatch.setattr(gate, "run_checks", run_checks)


def test_no_python_change_lets_claude_stop(repo):
    assert _stop(repo) is None


def test_real_failing_test_is_caught(repo):
    _break_tests(repo)
    result = _stop(repo)
    assert result["decision"] == "block" and "test_bad" in result["reason"]


def test_failing_test_blocks_twice_then_escalates(repo, fake_checks):
    _break_tests(repo)
    first, second, third = _stop(repo), _stop(repo), _stop(repo)
    assert first["decision"] == "block" and "1/2" in first["reason"]
    assert second["decision"] == "block" and "2/2" in second["reason"]
    assert third["continue"] is False and "사람" in third["stopReason"]


def test_passing_change_resets_counter(repo, fake_checks):
    _break_tests(repo)
    _stop(repo)
    (repo / "tests" / "test_bad.py").write_text("def test_bad():\n    assert True\n")
    assert _stop(repo) is None
    assert gate.load_state(repo)["s1"]["attempts"] == 0


def test_reset_gives_fresh_retries(repo, fake_checks):
    _break_tests(repo)
    for _ in range(3):
        _stop(repo)
    gate.reset({"session_id": "s1"}, repo)
    assert _stop(repo)["decision"] == "block"


def test_unchanged_passing_state_is_not_rechecked(repo, fake_checks, monkeypatch):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    assert _stop(repo) is None
    monkeypatch.setattr(gate, "run_checks", lambda root, files: pytest.fail("재검사함"))
    assert _stop(repo) is None


def test_feature_code_without_todo_update_fails(repo):
    feature = repo / "src" / "demo"
    feature.mkdir(parents=True)
    (feature / "TODO.md").write_text("# demo\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "todo")
    (feature / "calc.py").write_text("X = 1\n")
    assert gate._todo_failures(gate.changed_files(repo))
    (feature / "TODO.md").write_text("# demo\n- [x] calc\n")
    assert not gate._todo_failures(gate.changed_files(repo))


def test_mypy_covers_tests_and_changed_root_files(repo):
    (repo / "app.py").write_text("X = 1\n")
    targets = gate.mypy_targets(repo, gate.changed_files(repo))
    assert "tests" in targets and "app.py" in targets


def test_lint_error_is_reported(repo):
    (repo / "tests" / "test_lint.py").write_text(
        "import os\n\ndef test_x():\n    assert True\n"
    )
    failures = gate.run_checks(repo, gate.changed_files(repo))
    assert any(name == "ruff check" for name, _ in failures)


def test_change_hash_ignores_staging(repo):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    before = gate.change_hash(repo)
    _git(repo, "add", ".")
    assert gate.change_hash(repo) == before


def _handback(message: str, agent: str = "reviewer") -> dict:
    return {"agent_type": agent, "tool_input": {"message": message}}


@pytest.mark.parametrize(
    "report,approved",
    [
        ("승인 가능 여부: ✅ 승인", True),
        ("**승인 가능 여부**: ✅ 승인", True),
        ("승인 가능 여부: 승인", False),  # 정확한 승인 형식만 인정
        ("승인 가능 여부: 승인 불가", False),
        ("승인 가능 여부: 미승인 (보류)", False),
        ("승인 가능 여부: 수정 후 재검토", False),  # 이모지 없이 거절
        ("승인 가능 여부: ✅ 승인 / ❌ 수정 후 재검토", False),  # 템플릿 줄 그대로
        ("좋아 보입니다", False),  # 판정 줄 없음 → 거절
    ],
)
def test_review_verdict_is_read_from_verdict_line(repo, report, approved):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    gate.review_done(_handback(report), repo)
    assert gate.review_matches(repo) is approved


def test_review_record_matches_until_code_changes(repo):
    target = repo / "tests" / "test_new.py"
    target.write_text("def test_new():\n    assert True\n")
    assert not gate.review_matches(repo)
    gate.review_done(_handback("## 결과\n승인 가능 여부: ✅ 승인"), repo)
    assert gate.review_matches(repo)
    target.write_text("def test_new():\n    assert 1\n")
    assert not gate.review_matches(repo)


def test_review_not_required_without_python_changes(repo):
    (repo / "README.md").write_text("docs\n")
    assert gate.review_matches(repo)


def test_post_edit_reports_lint_error_to_claude(repo):
    bad = repo / "bad.py"
    bad.write_text("import os\n")
    result = subprocess.run(
        [sys.executable, str(Path(gate.__file__)), "post-edit"],
        input=json.dumps({"tool_input": {"file_path": str(bad)}}),
        capture_output=True,
        encoding="utf-8",
        cwd=repo,
    )
    assert result.returncode == 2
    assert "F401" in result.stderr


def _main(repo: Path, mode: str, payload: dict) -> subprocess.CompletedProcess:
    import os

    return subprocess.run(
        [sys.executable, str(Path(gate.__file__)), mode],
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


def test_only_gate_reset_command_resets_counter(repo, fake_checks):
    _break_tests(repo)
    for _ in range(3):
        _stop(repo)
    _main(repo, "reset", {"session_id": "s1", "command_name": "tdd"})
    assert gate.load_state(repo)["s1"]["attempts"] == 3
    _main(repo, "reset", {"session_id": "s1", "command_name": "gate-reset"})
    assert gate.load_state(repo)["s1"]["attempts"] == 0


def test_hanging_check_counts_as_failure_within_deadline(repo, monkeypatch):
    monkeypatch.setattr(gate, "DEADLINE_SECONDS", 3)
    (repo / "tests" / "test_hang.py").write_text(
        "import time\n\n\ndef test_hang():\n    time.sleep(30)\n"
    )
    started = time.monotonic()
    failures = gate.run_checks(repo, gate.changed_files(repo))
    assert time.monotonic() - started < 15
    assert any("시간 초과" in out for _, out in failures)


def test_broken_state_file_is_treated_as_empty(repo):
    state = repo / ".claude" / "state"
    state.mkdir(parents=True)
    (state / "gate.json").write_text("[]")
    assert gate.load_state(repo) == {}


def test_rejected_review_does_not_unlock_commit(repo):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    gate.review_done(
        {"last_assistant_message": "승인 가능 여부: ❌ 수정 후 재검토"}, repo
    )
    assert not gate.review_matches(repo)


def test_review_report_comes_from_handback_message(repo):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    handback = {
        "agent_type": "reviewer",
        "tool_input": {"message": "❌ 수정 후 재검토"},
    }
    gate.review_done(handback, repo)
    assert not gate.review_matches(repo)
    # 그 뒤 SubagentStop은 맺음말만(빈 문자열) 들고 와도 거절 기록을 덮어쓰지 않는다
    gate.review_done({"agent_type": "reviewer", "last_assistant_message": ""}, repo)
    assert not gate.review_matches(repo)


def test_every_review_round_is_logged_for_pr_body(repo):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    gate.review_done(_handback("🔴 버그\n승인 가능 여부: ❌ 수정 후 재검토"), repo)
    gate.review_done(_handback("승인 가능 여부: ✅ 승인"), repo)
    log = (repo / ".claude" / "state" / "gate-log.jsonl").read_text(encoding="utf-8")
    rounds = [json.loads(line) for line in log.splitlines()]
    assert [r["result"] for r in rounds] == ["review-rejected", "review-approved"]
    assert "🔴 버그" in rounds[0]["summary"]


def test_only_reviewer_can_record_review(repo):
    (repo / "tests" / "test_new.py").write_text("def test_new():\n    assert True\n")
    gate.review_done(
        {"agent_type": "builder", "last_assistant_message": "✅ 승인"}, repo
    )
    assert not gate.review_matches(repo)


def test_harness_config_change_needs_review(repo):
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")
    assert not gate.review_matches(repo)


def test_every_run_is_logged(repo, fake_checks):
    _break_tests(repo)
    _stop(repo)
    log = (repo / ".claude" / "state" / "gate-log.jsonl").read_text(encoding="utf-8")
    assert json.loads(log.splitlines()[-1])["result"] == "block"
