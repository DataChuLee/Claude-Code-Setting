"""에이전트 워크플로 구조 규칙 (LEARNING: 조용한 성공 환류).

claude-code-action은 '성공'으로 끝나도 결과물(PR·댓글)이 없을 수 있다 (HARNESS Phase 4 실패 5·10).
그래서 에이전트를 돌리는 모든 job은 그 뒤에 결과물을 확인하는 단계와, 실패를 사람에게 알리는 단계를 가져야 한다.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent / "workflows"


def _agent_jobs() -> list:
    jobs = []
    for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in doc.get("jobs", {}).items():
            steps = job.get("steps", [])
            if any(
                str(s.get("uses", "")).startswith("anthropics/claude-code-action")
                for s in steps
            ):
                job_id = f"{path.name}:{name}"
                jobs.append(pytest.param(job_id, steps, id=job_id))
    return jobs


def test_agent_jobs_exist() -> None:
    # spec·build·fix·review — 0이면 아래 검사가 아무것도 안 봄
    assert len(_agent_jobs()) >= 4


@pytest.mark.parametrize(("job", "steps"), _agent_jobs())
def test_agent_job_checks_outcome_then_notifies_on_failure(
    job: str, steps: list[dict]
) -> None:
    agent = max(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    after = steps[agent + 1 :]
    check = next(
        (
            i
            for i, s in enumerate(after)
            if str(s.get("name", "")).startswith("결과 확인")
        ),
        None,
    )
    assert check is not None, f"{job}: claude 단계 뒤에 '결과 확인' 단계가 없다"
    notifies = [str(s.get("if", "")) for s in after[check + 1 :]]
    assert any("failure()" in c and "!failure()" not in c for c in notifies), (
        f"{job}: '결과 확인' 뒤에 failure()로 사람에게 알리는 단계가 없다"
    )
