"""spec_format.py: SPEC 질문마다 `제안:`이 있어야 한다 (LEARNING: SPEC 답 전달 — 2회째에 강제 장치로)."""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spec_format  # noqa: E402

TAIL = "고친 SPEC이 다시 게시되지 않으면 모든 질문은 제안대로 결정된 것으로 본다. 다른 답이면 고친 SPEC을 소유자 댓글로 다시 게시한다"


def _spec(questions: str, tail: str = TAIL) -> str:
    return f"<!-- agent-spec -->\n# x SPEC\n## 인수조건\n- [ ] a\n\n## 질문 (답변 필요)\n{questions}\n\n{tail}\n"


def test_every_question_has_proposal_ok() -> None:
    # 이슈 #17 실제 형식: 한 줄에 질문과 제안
    body = _spec(
        "1. 위치는? 제안: `src/versioning/`.\n2. 앞자리 0은?\n   제안: ValueError."
    )
    assert spec_format.problems(body) == []


def test_question_without_proposal_is_reported() -> None:
    # 이슈 #11 실제 1번 질문: 제안 없이 "맞는가?"로 끝남 → build가 멈출 수 있던 형식
    body = _spec("1. 30자 제한은 slug만인가. 맞는가?\n2. 이름은? 제안: 그대로.")
    assert spec_format.problems(body) == ["질문 1에 '제안:'이 없다"]


def test_missing_closing_line_is_reported() -> None:
    body = _spec("1. 이름은? 제안: 그대로.", tail="답변 후 라벨을 붙이세요")
    assert spec_format.problems(body) == ["마지막에 '제안대로 결정' 문구가 없다"]


def test_no_question_section_is_ok() -> None:
    assert (
        spec_format.problems("<!-- agent-spec -->\n# x\n## 인수조건\n- [ ] a\n") == []
    )


def test_question_section_ends_at_next_heading() -> None:
    body = _spec("1. 이름은? 제안: 그대로.") + "## 부록\n1. 이건 질문이 아니다\n"
    assert spec_format.problems(body) == []


def test_loose_formats_do_not_slip_through() -> None:
    # 재점검 🔴: 형식 이탈이 곧 통과 경로였다 — 글머리 질문, ### 제목, 굵은 제목, 우연한 "제안" 글자
    assert spec_format.problems(_spec("- 이름은?\n- 위치는? 제안: src.")) == [
        "질문 1에 '제안:'이 없다"
    ]
    assert spec_format.problems(_spec("1. 맞는가?").replace("## 질문", "### 질문")) == [
        "질문 1에 '제안:'이 없다"
    ]
    assert spec_format.problems(
        _spec("1. 맞는가?").replace("## 질문 (답변 필요)", "**질문**")
    ) == ["질문 1에 '제안:'이 없다"]
    assert spec_format.problems(_spec("1. 사용자 제안 기능의 범위는?")) == [
        "질문 1에 '제안:'이 없다"
    ]


def test_empty_body_is_a_problem() -> None:
    assert spec_format.problems("") == ["SPEC 본문이 비어 있다"]


def test_main_exit_codes(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO(_spec("1. 맞는가?")))
    assert spec_format.main() == 1
    assert "질문 1" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdin", io.StringIO(_spec("1. 이름은? 제안: 그대로.")))
    assert spec_format.main() == 0
