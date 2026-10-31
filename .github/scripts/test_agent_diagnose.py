"""agent_diagnose.py: 에이전트가 결과 없이 끝났을 때 이유를 로그에 남긴다 (HARNESS P4 실패 10, 후속 fix 실전)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agent_diagnose  # noqa: E402

RESULT = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "num_turns": 9,
    "result": "끝",
    "permission_denials": [
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr view 12 --comments | head"},
        },
        {"tool_name": "Edit", "tool_input": {"file_path": "tests/test_x.py"}},
    ],
}


def test_summarize_reports_end_and_denied_tools() -> None:
    lines = agent_diagnose.summarize([{"type": "system"}, RESULT])
    assert lines[0] == "종료: success is_error=False 턴=9"
    assert "끝" in lines[1]
    assert "거부된 도구: Bash gh pr view 12 --comments | head" in lines
    assert "거부된 도구: Edit tests/test_x.py" in lines


def test_summarize_single_object_and_missing_result() -> None:
    assert agent_diagnose.summarize(RESULT)[0].startswith("종료: success")
    assert agent_diagnose.summarize([{"type": "system"}])[1] == "마지막 답변:\n(없음)"


def test_summarize_truncates_long_answer_and_target() -> None:
    long = dict(
        RESULT,
        result="x" * 5000,
        permission_denials=[
            {"tool_name": "Bash", "tool_input": {"command": "y" * 1000}}
        ],
    )
    lines = agent_diagnose.summarize(long)
    assert len(lines[1]) <= len("마지막 답변:\n") + 2000
    assert len(lines[2]) <= len("거부된 도구: Bash ") + 300


def test_summarize_odd_shapes_keep_end_and_answer_lines() -> None:
    # 리뷰 🟡: 예상 밖 형식이면 jq는 앞 두 줄은 남겼다. 예외로 통째로 사라지면 안 된다
    for denials in (5, ["x"], [{"tool_name": "Bash", "tool_input": "s"}]):
        lines = agent_diagnose.summarize(dict(RESULT, permission_denials=denials))
        assert lines[0].startswith("종료: success") and "끝" in lines[1]


def test_gate_failures_keeps_only_block_and_escalate() -> None:
    log = [
        json.dumps({"result": "pass"}),
        json.dumps({"result": "block", "failures": ["pytest"]}),
        "{broken",
        json.dumps({"result": "escalate", "failures": ["ruff"]}),
    ]
    assert [json.loads(x)["result"] for x in agent_diagnose.gate_failures(log)] == [
        "block",
        "escalate",
    ]


def test_main_without_execution_file(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert agent_diagnose.main([str(tmp_path / "none.json")]) == 0
    assert "실행 기록 없음" in capsys.readouterr().out


def test_main_prints_gate_and_result(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    ex = tmp_path / "exec.json"
    ex.write_text(json.dumps([RESULT]), encoding="utf-8")
    gate = tmp_path / "gate-log.jsonl"
    gate.write_text(
        json.dumps({"result": "escalate", "failures": ["mypy"]}) + "\n",
        encoding="utf-8",
    )
    assert agent_diagnose.main([str(ex), str(gate)]) == 0
    out = capsys.readouterr().out
    assert "mypy" in out and "거부된 도구: Edit tests/test_x.py" in out
