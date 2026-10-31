import pytest

from versioning.bump import bump


@pytest.mark.parametrize(
    ("version", "part", "expected"),
    [
        ("1.4.2", "minor", "1.5.0"),
        ("1.4.2", "major", "2.0.0"),
        ("1.4.2", "patch", "1.4.3"),
        ("0.0.0", "patch", "0.0.1"),
        ("1.9.9", "minor", "1.10.0"),
        ("1.9.9", "patch", "1.9.10"),
    ],
)
def test_bump_valid_version_returns_next(version, part, expected):
    assert bump(version, part) == expected


@pytest.mark.parametrize(
    "version",
    ["1.2", "1.2.3.4", "a.b.c", "", "1.2.-3", "01.2.3", "1.2.3\n", "１.２.３"],
)
def test_bump_malformed_version_raises_value_error(version):
    with pytest.raises(ValueError):
        bump(version, "patch")


@pytest.mark.parametrize("version", ["v1.2.3", "1.2.3-rc.1", "1.2.3+sha"])
def test_bump_prefix_or_suffix_version_raises_value_error(version):
    with pytest.raises(ValueError):
        bump(version, "patch")


@pytest.mark.parametrize("part", ["Minor", "build", "", " minor"])
def test_bump_unknown_part_raises_value_error(part):
    with pytest.raises(ValueError):
        bump("1.2.3", part)


@pytest.mark.parametrize("version", [None, 123])
def test_bump_non_string_version_raises_value_error(version):
    with pytest.raises(ValueError):
        bump(version, "patch")  # type: ignore[arg-type]
