import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pr_size import count_lines

SRC = Path(__file__).resolve().parent.parent / "src"


def f(name, add=0, dele=0):
    return {"filename": name, "additions": add, "deletions": dele}


def test_count_lines_py_file_returns_sum():
    assert count_lines([f("a.py", 3, 2)]) == 5


def test_count_lines_readme_md_returns_zero():
    assert count_lines([f("README.md", 10)]) == 0


@pytest.mark.parametrize("name", ["docs/PLAN.md", "src/x/SPEC.md"])
def test_count_lines_human_md_not_counted(name):
    assert count_lines([f(name, 4, 1)]) == 0


@pytest.mark.parametrize(
    "name",
    [
        ".claude/agents/reviewer.md",
        ".claude/skills/spec/SKILL.md",
        "CLAUDE.md",
        "src/x/CLAUDE.md",
        ".claude/hooks/guard.py",
    ],
)
def test_count_lines_harness_files_counted(name):
    assert count_lines([f(name, 4, 1)]) == 5


def test_count_lines_name_only_ending_with_claude_md_not_counted():
    assert count_lines([f("docs/NOTCLAUDE.md", 4, 1)]) == 0


def test_count_lines_uppercase_extension_counted():
    assert count_lines([f("docs/A.MD", 2, 1)]) == 3


def test_count_lines_empty_list_returns_zero():
    assert count_lines([]) == 0


def test_count_lines_mixed_sums_only_counted():
    items = [f("a.py", 1, 1), f("README.md", 50), f("CLAUDE.md", 2, 0)]
    assert count_lines(items) == 4


def test_count_lines_rename_uses_new_filename():
    item = {**f("docs/new.md", 5), "previous_filename": "CLAUDE.md"}
    assert count_lines([item]) == 0


def test_count_lines_pages_sums_all_with_empty_page():
    assert count_lines([[f("a.py", 1, 0)], [], [f("b.py", 0, 2)]]) == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"a": 1},
        "x",
        3,
        [3],
        [{"additions": 1, "deletions": 1}],
        [{"filename": "a.py", "deletions": 1}],
        [{"filename": "a.py", "additions": 1}],
        [{"filename": "a.py", "additions": "1", "deletions": 0}],
        [{"filename": "a.py", "additions": 1.5, "deletions": 0}],
        [{"filename": "a.py", "additions": True, "deletions": 0}],
        [{"filename": 1, "additions": 1, "deletions": 0}],
        [[[f("a.py", 1)]]],
    ],
)
def test_count_lines_malformed_input_raises(bad):
    with pytest.raises(ValueError):
        count_lines(bad)


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pr_size", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


def test_cli_valid_file_prints_number(tmp_path):
    p = tmp_path / "in.json"
    p.write_text(json.dumps([f("a.py", 3, 2)]))
    r = run_cli(str(p))
    assert (r.returncode, r.stdout) == (0, "5\n")


def test_cli_missing_file_fails_without_stdout(tmp_path):
    r = run_cli(str(tmp_path / "none.json"))
    assert r.returncode != 0 and r.stdout == "" and r.stderr


def test_cli_invalid_json_fails_without_stdout(tmp_path):
    p = tmp_path / "in.json"
    p.write_text("not json")
    r = run_cli(str(p))
    assert r.returncode != 0 and r.stdout == "" and r.stderr


def test_cli_non_array_fails_without_stdout(tmp_path):
    p = tmp_path / "in.json"
    p.write_text('{"a": 1}')
    r = run_cli(str(p))
    assert r.returncode != 0 and r.stdout == "" and r.stderr


def test_cli_no_argument_fails():
    r = run_cli()
    assert r.returncode != 0 and r.stdout == ""
