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


@pytest.mark.parametrize(("job", "steps"), _agent_jobs())
def test_agent_job_diagnoses_why_it_stopped(job: str, steps: list[dict]) -> None:
    # 결과가 없을 때 "왜"가 로그에 없으면 원인을 못 찾는다 (P4 실패 10 build, 후속 fix 실전 — 2회)
    agent = max(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    assert steps[agent].get("id") == "claude", f"{job}: claude 단계에 id: claude가 없다"
    diag = [
        i
        for i, s in enumerate(steps)
        if "agent_diagnose.py" in str(s.get("run", ""))
        and "steps.claude.outputs.execution_file" in str(s.get("env", {}))
    ]
    assert diag and diag[0] > agent, f"{job}: claude 단계 뒤에 진단 단계가 없다"
    step = steps[diag[0]]
    cond, run = str(step.get("if", "")), str(step.get("run", ""))
    assert "failure()" in cond or "always()" in cond, f"{job}: 실패할 때 돌지 않는다"
    # 모델 출력이 워크플로 명령(::error:: 등)으로 해석되지 않게
    assert "::stop-commands::" in run, f"{job}: stop-commands 감싸기가 없다"
    # 샌드박스 밖 run 단계다. 에이전트가 고칠 수 있는 작업 트리 파일을 실행하지 않는다 (리뷰 🔴)
    assert '"$RUNNER_TEMP/agent_diagnose.py"' in run, (
        f"{job}: 실행 전 사본을 쓰지 않는다"
    )


@pytest.mark.parametrize(("job", "steps"), _agent_jobs())
def test_agent_job_judges_with_copy_made_before_agent(
    job: str, steps: list[dict]
) -> None:
    # 판정·진단 스크립트는 에이전트 실행 전에 $RUNNER_TEMP로 떠 둔 사본을 쓴다
    agent = max(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    before = " ".join(str(s.get("run", "")) for s in steps[:agent])
    after = " ".join(str(s.get("run", "")) for s in steps[agent + 1 :])
    for script in re.findall(r"\.github/scripts/(\w+\.py)", after):
        pytest.fail(f"{job}: 에이전트 뒤에 작업 트리의 {script}를 실행한다")
    for script in re.findall(r'"\$RUNNER_TEMP/(\w+\.py)"', after):
        assert script in before and "RUNNER_TEMP" in before, (
            f"{job}: {script} 사본을 에이전트 실행 전에 만들지 않는다"
        )
    # PR 브랜치를 체크아웃한 job(review·fix)은 작업 트리가 이전 라운드 에이전트의 코드다
    # → 사본도 기본 브랜치 판에서 떠야 한다 (리뷰 2차 🔴)
    if any(
        s.get("with", {}).get("ref")
        for s in steps
        if "checkout" in str(s.get("uses", ""))
    ):
        assert 'git show "origin/' in before and "cp .github/scripts" not in before, (
            f"{job}: PR 브랜치 job인데 사본을 기본 브랜치 판에서 뜨지 않는다"
        )


def test_build_requires_owner_thumbs_up_before_agent() -> None:
    # 봇 SPEC 승인은 모델이 아니라 에이전트 실행 전 단계가 판단한다 (LEARNING: 안전 조건을 모델 순종에 맡기지 않음)
    doc = yaml.safe_load((WORKFLOWS / "agent-build.yml").read_text(encoding="utf-8"))
    steps = doc["jobs"]["build"]["steps"]
    agent = next(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith("anthropics/claude-code-action")
    )
    assert any("spec_approval.py" in str(s.get("run", "")) for s in steps[:agent])


def test_spec_outcome_check_runs_format_check_copy() -> None:
    # 질문마다 제안 — 스킬 문장이 아니라 결과 확인 단계가 검사한다 (LEARNING: SPEC 답 전달 2회째)
    doc = yaml.safe_load((WORKFLOWS / "agent-spec.yml").read_text(encoding="utf-8"))
    steps = doc["jobs"]["spec"]["steps"]
    check = next(s for s in steps if str(s.get("name", "")).startswith("결과 확인"))
    assert '"$RUNNER_TEMP/spec_format.py"' in str(check.get("run", ""))
