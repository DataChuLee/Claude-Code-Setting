"""observe.py gate-log 요약."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import observe  # noqa: E402


def _line(**entry: object) -> str:
    return json.dumps(entry)


def test_summarize_counts_results_failed_checks_and_rejection_rate() -> None:
    lines = [
        _line(session="a", result="pass"),
        _line(session="a", result="block", attempts=1, failures=["pytest", "ruff"]),
        _line(session="b", result="escalate", attempts=3, failures=["pytest"]),
        _line(result="review-rejected", summary="x"),
        _line(result="review-approved", summary="y"),
        _line(result="review-approved", summary="z"),
    ]
    s = observe.summarize(lines)
    assert s["results"] == {
        "pass": 1,
        "block": 1,
        "escalate": 1,
        "review-rejected": 1,
        "review-approved": 2,
    }
    assert s["checks"] == {"pytest": 2, "ruff": 1}
    assert s["escalated"] == ["b"]
    assert s["rejection_rate"] == 1 / 3
    assert s["broken"] == 0


def test_summarize_broken_and_blank_lines_are_counted_not_fatal() -> None:
    s = observe.summarize(["{not json", "", "[1]", _line(result="pass")])
    assert s["broken"] == 2
    assert s["results"] == {"pass": 1}


def test_summarize_empty_log_has_no_rejection_rate() -> None:
    s = observe.summarize([])
    assert s["results"] == {}
    assert s["rejection_rate"] is None


def test_main_missing_file_fails_instead_of_reporting_zero(
    tmp_path: Path, capsys
) -> None:  # type: ignore[no-untyped-def]
    # 경로를 잘못 넘기면 "(없음) 0" 표가 나와 '실패 0건'으로 오해한다 (리뷰 🟡)
    assert observe.main([str(tmp_path / "nope.jsonl")]) == 1
    assert "nope.jsonl" in capsys.readouterr().err


def test_main_reads_given_files_and_prints_table(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    log = tmp_path / "gate-log.jsonl"
    log.write_text(_line(result="review-rejected") + "\n", encoding="utf-8")
    assert observe.main([str(log)]) == 0
    out = capsys.readouterr().out
    assert "| review-rejected | 1 |" in out
    assert "100%" in out
