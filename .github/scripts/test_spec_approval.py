"""spec_approval.py: 봇이 쓴 SPEC은 소유자의 👍가 있어야 승인 (HARNESS P4 한계 — 주입된 실행이 봇 이름으로 가짜 SPEC을 다는 경로)."""

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spec_approval  # noqa: E402

OWNER = "DataChuLee"


def _r(login: str, content: str = "+1") -> dict:
    return {"user": {"login": login}, "content": content}


def test_owner_thumbs_up_approves() -> None:
    assert spec_approval.approved([_r("someone"), _r(OWNER)], OWNER)


def test_other_users_thumbs_up_does_not_approve() -> None:
    assert not spec_approval.approved([_r("someone"), _r("github-actions[bot]")], OWNER)


def test_owner_other_reaction_does_not_approve() -> None:
    assert not spec_approval.approved([_r(OWNER, "heart"), _r(OWNER, "-1")], OWNER)


def test_no_reactions_does_not_approve() -> None:
    assert not spec_approval.approved([], OWNER)


def test_owner_login_is_exact_match() -> None:
    assert not spec_approval.approved([_r(OWNER + "x"), _r(OWNER.lower())], OWNER)


def test_main_exit_1_with_reason(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps([_r("someone")])))
    assert spec_approval.main(["--owner", OWNER]) == 1
    assert "👍" in capsys.readouterr().out


def test_main_exit_0_when_owner_approved(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps([_r(OWNER)])))
    assert spec_approval.main(["--owner", OWNER]) == 0


def test_main_null_input_is_not_approved(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "stdin", io.StringIO("null"))
    assert spec_approval.main(["--owner", OWNER]) == 1
