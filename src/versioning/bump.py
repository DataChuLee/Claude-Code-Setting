import re

_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", re.ASCII)


def bump(version: str, part: str) -> str:
    """`MAJOR.MINOR.PATCH`의 `part`(major|minor|patch)를 올린 다음 버전을 돌려준다."""
    if not isinstance(version, str) or not isinstance(part, str):
        raise ValueError("version과 part는 문자열이어야 한다")
    match = _VERSION.fullmatch(version)
    if match is None:
        raise ValueError(f"잘못된 버전: {version!r}")
    major, minor, patch = (int(g) for g in match.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"알 수 없는 부분: {part!r}")
