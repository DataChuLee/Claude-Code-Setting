---
name: eval
description: "LLM·RAG 기능을 Eval-Driven으로 검증한다. 프롬프트를 쓰기 전에 평가셋과 채점기를 먼저 만들고, 실행해 SPEC의 합격선과 비교한다. 정답이 하나로 정해지지 않는 LLM 출력용 (결정적 코드는 tdd)."
when_to_use: "'평가해줘', 'eval', '답변 품질 측정', '프롬프트 바꿨는데 나아졌어?', '정확도 확인', RAG·LLM 기능을 만들거나 프롬프트·모델·검색 방식을 바꿀 때. 예: 'RAG 답변 품질 평가해줘'"
argument-hint: "[기능명]"
---

# Eval — 평가 기준 먼저, 프롬프트는 나중

대상: $ARGUMENTS

## 순서
1. `src/<기능>/SPEC.md`의 **평가 기준**(지표·합격선)을 확인. 없으면 `spec` 스킬로 먼저 정한다
2. **평가셋 먼저** — `tests/eval/<기능>.jsonl`: 한 줄에 `{"question", "expected", "source"}` (최소 10문항, 쉬운 것·어려운 것·답이 없는 것 포함)
3. **채점기** — `tests/eval/test_<기능>_eval.py`, 테스트에 `@pytest.mark.eval`
   - 결정적 채점 우선: 정답 키워드 포함, 근거 문서 인용 여부, 형식
   - 필요할 때만 LLM 채점(LLM-as-judge), 채점 기준을 프롬프트에 명시
   - 전체 점수를 출력하고 합격선 미만이면 실패
4. 실행: `python -m pytest -m eval -q` (API 키 `OPENAI_API_KEY`는 사용자가 환경변수로 등록. 없으면 건너뛰고 알린다)
5. 결과(점수, 실패 문항)를 `src/<기능>/TODO.md` 리뷰 기록에 남긴다. 변경 전후 점수를 비교한다

## 주의
- `eval` 마커 테스트는 API 비용이 들어 **Stop 게이트에서 제외**된다 (pyproject `addopts = -m 'not eval'`). 이 스킬이 명시적으로 돌린다
- 단위 테스트에서는 LLM 호출을 mock으로 대체 (키 없이 돌아야 함)
- 키 값을 출력하거나 파일에 쓰지 않는다 (guard가 차단)
