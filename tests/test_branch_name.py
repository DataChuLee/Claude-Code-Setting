import re

import pytest

from branch_name import make_branch_name


def slug_of(title: str) -> str:
    return make_branch_name(1, title).removeprefix("agent/1-")


def test_make_branch_name_normal_title_returns_agent_prefixed_name():
    assert make_branch_name(12, "Add login page") == "agent/12-add-login-page"


def test_slug_uppercase_title_is_lowercased():
    assert slug_of("Fix API Bug") == "fix-api-bug"


def test_slug_digits_are_kept():
    assert slug_of("Bump v2 to 3") == "bump-v2-to-3"


def test_slug_consecutive_separators_collapse_to_one_hyphen():
    assert slug_of("a  --  b!!c") == "a-b-c"


def test_slug_leading_trailing_separators_are_removed():
    assert slug_of("  !!hello!!  ") == "hello"


def test_slug_korean_mixed_is_treated_as_separator():
    assert slug_of("로그인 login 버그") == "login"


def test_slug_accented_char_is_treated_as_separator():
    assert slug_of("café") == "caf"


def test_slug_kelvin_sign_is_not_lowercased_into_ascii():
    assert slug_of("K") == "issue"


def test_slug_korean_only_falls_back_to_issue():
    assert slug_of("로그인 버그") == "issue"


@pytest.mark.parametrize("title", ["", "   ", "!!!"])
def test_slug_empty_or_symbols_only_falls_back_to_issue(title):
    assert slug_of(title) == "issue"


def test_slug_exactly_30_chars_is_kept():
    title = "a" * 10 + " " + "b" * 10 + " " + "c" * 8  # 10+1+10+1+8 = 30
    assert slug_of(title) == "a" * 10 + "-" + "b" * 10 + "-" + "c" * 8
    assert len(slug_of(title)) == 30


def test_slug_over_30_chars_cuts_at_last_hyphen_within_limit():
    title = "a" * 10 + " " + "b" * 10 + " " + "c" * 9 + " " + "d" * 5
    # 앞 30자는 'a*10-b*10-c*9' (단어 중간), 31번째가 'c'
    result = slug_of(title)
    assert result == "a" * 10 + "-" + "b" * 10
    assert len(result) <= 30
    assert not result.endswith("-")


def test_slug_over_30_chars_with_hyphen_at_31st_keeps_first_30():
    title = "a" * 10 + " " + "b" * 10 + " " + "c" * 8 + " " + "dd"  # 31번째 문자가 '-'
    assert slug_of(title) == "a" * 10 + "-" + "b" * 10 + "-" + "c" * 8


def test_slug_single_word_over_30_chars_is_cut_at_30():
    assert slug_of("x" * 50) == "x" * 30


@pytest.mark.parametrize(
    "title",
    [
        "Hello, World!",
        "  ---  ",
        "한글 title 가나다 " * 5,
        "word " * 20,
        "é" * 40,
        "a-" * 40,
    ],
)
def test_slug_invariants_hold_for_any_input(title):
    slug = slug_of(title)
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug)
    assert len(slug) <= 30


@pytest.mark.parametrize("number", [0, -1, -100])
def test_make_branch_name_non_positive_number_raises_value_error(number):
    with pytest.raises(ValueError):
        make_branch_name(number, "title")


def test_make_branch_name_same_input_returns_same_result():
    assert make_branch_name(5, "Same Title") == make_branch_name(5, "Same Title")
