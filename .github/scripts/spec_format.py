"""SPEC 댓글 형식 검사: 질문마다 `제안:`, 끝에 '제안대로 결정' 문구.

build는 답 댓글을 읽지 않아 제안이 곧 기본 결정이다. 제안 없는 질문이 있으면 build가 멈춘다
(HARNESS P4 실패 10 1차, P5 이슈 #11 — 2회째라 스킬 문장에서 기계 검사로 올림, LEARNING 절차 3).
입력: stdin의 SPEC 본문. 문제가 있으면 exit 1 → spec 워크플로의 실패 알림.
"""

import re
import sys

# 형식 이탈이 곧 통과 경로가 되지 않게 넓게 잡는다: ##·### 제목, **질문** 굵은 제목, 번호·글머리 항목
QUESTIONS = re.compile(
    r"^(?:#{2,}\s*|\*\*)질문.*?$(.*?)(?=^#{1,}\s|^\*\*\S|\Z)", re.M | re.S
)
ITEM = re.compile(r"^\s*(?:\d+\.|[-*])\s", re.M)
PROPOSAL = re.compile(r"제안\s*[:：]")  # 질문 문장 속 우연한 "제안" 글자는 세지 않는다


def problems(body: str) -> list[str]:
    if not body.strip():
        return ["SPEC 본문이 비어 있다"]
    section = QUESTIONS.search(body)
    if not section:
        return []
    # 맺음 문구 속 "제안"이 마지막 질문의 제안으로 세지지 않게, 질문 범위에서 뺀다
    closing = "제안대로 결정" in section.group(1)
    text = "\n".join(
        ln for ln in section.group(1).splitlines() if "제안대로 결정" not in ln
    )
    starts = list(ITEM.finditer(text))
    found = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        if not PROPOSAL.search(text[m.start() : end]):
            found.append(f"질문 {i + 1}에 '제안:'이 없다")
    if starts and not closing:
        found.append("마지막에 '제안대로 결정' 문구가 없다")
    return found


def main() -> int:
    # 플랫폼 기본 인코딩(Windows cp949)에 기대지 않는다
    body = (
        sys.stdin.buffer.read().decode("utf-8")
        if hasattr(sys.stdin, "buffer")
        else sys.stdin.read()
    )
    found = problems(body)
    for p in found:
        print(f"SPEC 형식: {p} (spec 스킬 CI 모드 — 질문마다 제안을 쓴다)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
