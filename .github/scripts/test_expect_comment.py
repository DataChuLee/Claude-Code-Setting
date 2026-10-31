"""expect_comment.py: 에이전트가 성공했는데 결과 댓글이 없는 경우를 잡는다 (LEARNING: 조용한 성공)."""

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import expect_comment  # noqa: E402

BOT = "github-actions[bot]"  # REST 기준 (GraphQL은 "github-actions")


def _c(id: int, login: str = BOT, body: str = "<!-- agent-spec -->\nSPEC") -> dict:
    return {"id": id, "user": {"login": login}, "body": body}


def test_found_new_bot_comment_with_marker() -> None:
    assert expect_comment.found(
        [_c(5)], after_id=4, author=BOT, prefix="<!-- agent-spec -->"
    )


def test_found_same_id_is_old_comment() -> None:
    assert not expect_comment.found([_c(4)], after_id=4, author=BOT, prefix="")


def test_found_other_author_is_ignored() -> None:
    assert not expect_comment.found(
        [_c(5, login="someone")], after_id=0, author=BOT, prefix=""
    )


def test_found_graphql_login_does_not_match_rest_author() -> None:
    assert not expect_comment.found(
        [_c(5, login="github-actions")], after_id=0, author=BOT, prefix=""
    )


def test_found_missing_marker_is_ignored() -> None:
    assert not expect_comment.found(
        [_c(5, body="질문이 있습니다")],
        after_id=0,
        author=BOT,
        prefix="<!-- agent-spec -->",
    )


def test_found_empty_list() -> None:
    assert not expect_comment.found([], after_id=0, author=BOT, prefix="")


def test_main_exit_1_with_reason_when_missing(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps([_c(3)])))
    code = expect_comment.main(
        ["--after-id", "3", "--author", BOT, "--prefix", "<!-- agent-spec -->"]
    )
    assert code == 1
    assert "<!-- agent-spec -->" in capsys.readouterr().out


def test_main_exit_0_when_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps([_c(9)])))
    assert expect_comment.main(["--after-id", "3", "--author", BOT]) == 0
