import json
import sys

from pr_size.counter import count_lines


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("사용법: python -m pr_size <JSON 파일>", file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            data = json.load(fh)
        total = count_lines(data)
    except (OSError, ValueError) as e:  # JSONDecodeError는 ValueError 하위
        print(f"오류: {e}", file=sys.stderr)
        return 1
    print(total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
