"""워크플로 구조 규칙.

1. 조용한 성공 환류 (LEARNING): claude-code-action은 '성공'으로 끝나도 결과물(PR·댓글)이 없을 수 있다
   (HARNESS Phase 4 실패 5·10). 에이전트를 돌리는 모든 job은 결과 확인 단계와 실패 알림 단계를 가진다.
2. 공급망: 외부 action은 태그가 아니라 커밋 SHA로 고정한다 (태그는 옮겨질 수 있고, 이 job들은 쓰기 토큰·OAuth 토큰을 쥔다).
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent / "workflows"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _workflow_files() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def _external_uses() -> list:
    found = []
    for path in _workflow_files():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in doc.get("jobs", {}).items():
            # job 수준 uses(재사용 워크플로)와 step 수준 uses 모두. ./ 로 시작하면 이 저장소 파일
            for uses in [
                job.get("uses"),
                *(s.get("uses") for s in job.get("steps", [])),
            ]:
                if uses and not str(uses).startswith("./"):
                    found.append(
                        pytest.param(str(uses), id=f"{path.name}:{name}:{uses}")
                    )
    return found


def test_external_actions_exist() -> None:
    assert _external_uses()  # 0이면 아래 검사가 아무것도 안 봄


@pytest.mark.parametrize("uses", _external_uses())
def test_external_action_is_pinned_to_commit_sha(uses: str) -> None:
    assert PINNED.match(uses), f"{uses}: 커밋 SHA(40자리)로 고정하고 태그는 주석으로"


def _agent_jobs() -> list:
    jobs = []
    for path in _workflow_files():
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
