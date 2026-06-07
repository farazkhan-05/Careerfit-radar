from __future__ import annotations

from typing import Any, cast

from backend.workflows.job_discovery_graph import (
    JobDiscoveryState,
    JobDiscoveryWorkflow,
    JobDiscoveryWorkflowDependencies,
    WorkflowNodeConfig,
    WorkflowRunRepository,
)


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.saved_states: list[JobDiscoveryState] = []

    def save_state(self, state: JobDiscoveryState) -> None:
        self.saved_states.append(state.copy())

    def get_run(self, run_id: str) -> JobDiscoveryState | None:
        for state in reversed(self.saved_states):
            if state["run_id"] == run_id:
                return state
        return None

    def list_runs(self, *, status: str | None = None) -> tuple[JobDiscoveryState, ...]:
        states = self.saved_states
        if status is not None:
            states = [state for state in states if state["status"] == status]
        return tuple(states)


def test_job_discovery_workflow_runs_required_nodes_and_builds_shortlist() -> None:
    dependencies = JobDiscoveryWorkflowDependencies(
        load_preferences=lambda: {"minimum_fit_score": 70},
        fetch_sources=lambda state: [
            {
                "source_name": "greenhouse",
                "status": "success",
                "jobs": [{"source_job_id": "1", "title": "AI Backend Developer"}],
            }
        ],
        normalise_jobs=lambda state: [
            {"id": "job-1", "title": "AI Backend Developer", "source": "greenhouse"}
        ],
        hard_filter=lambda state: {
            "accepted_jobs": state["normalized_jobs"],
            "rejected_jobs": [],
        },
        deduplicate_jobs=lambda state: {
            "canonical_jobs": state["accepted_jobs"],
            "duplicate_jobs": [],
        },
        extract_requirements=lambda state: [
            {"job_id": "job-1", "required_skills": ["Python"]}
        ],
        embed_jobs=lambda state: [{"job_id": "job-1", "text_hash": "hash"}],
        store_jobs=lambda state: state["canonical_jobs"],
        score_jobs=lambda state: [
            {"job_id": "job-1", "final_score": 88},
            {"job_id": "job-2", "final_score": 62},
        ],
        gap_analysis=lambda state: [{"job_id": "job-1", "missing_required_skills": []}],
    )
    repository = FakeWorkflowRepository()
    workflow = JobDiscoveryWorkflow(
        dependencies=dependencies,
        repository=cast(WorkflowRunRepository, repository),
        config=WorkflowNodeConfig(minimum_shortlist_score=70),
    )

    state = workflow.run({"run_id": "test-run"})

    assert state["status"] == "completed"
    assert [item["job_id"] for item in state["shortlist"]] == ["job-1"]
    assert repository.get_run("test-run") == state
    assert repository.list_runs(status="completed")[-1]["run_id"] == "test-run"
    expected_nodes = {
        "start_run_node",
        "load_preferences_node",
        "fetch_sources_node",
        "normalise_jobs_node",
        "hard_filter_node",
        "deduplicate_jobs_node",
        "extract_requirements_node",
        "embed_jobs_node",
        "store_jobs_node",
        "score_jobs_node",
        "gap_analysis_node",
        "build_shortlist_node",
        "finish_run_node",
    }
    assert expected_nodes.issubset({event["node"] for event in state["history"]})


def test_source_failures_do_not_stop_workflow_execution() -> None:
    dependencies = JobDiscoveryWorkflowDependencies(
        fetch_sources=lambda state: [
            {
                "source_name": "lever",
                "status": "failed",
                "error_message": "network timeout",
            }
        ],
        score_jobs=lambda state: [{"job_id": "fallback", "final_score": 72}],
    )
    workflow = JobDiscoveryWorkflow(dependencies=dependencies)

    state = workflow.run({"run_id": "source-failure-run"})

    assert state["status"] == "completed_with_errors"
    assert state["errors"][0]["source"] == "lever"
    assert state["shortlist"] == [{"job_id": "fallback", "final_score": 72}]
    assert state["history"][-1]["node"] == "finish_run_node"


def test_node_exceptions_are_recorded_and_later_nodes_continue() -> None:
    def failing_requirements(state: JobDiscoveryState) -> list[dict[str, Any]]:
        raise RuntimeError("Gemini failed")

    dependencies = JobDiscoveryWorkflowDependencies(
        extract_requirements=failing_requirements,
        score_jobs=lambda state: [{"job_id": "job-1", "final_score": 75}],
    )
    workflow = JobDiscoveryWorkflow(dependencies=dependencies)

    state = workflow.run({"run_id": "node-error-run"})

    assert state["status"] == "completed_with_errors"
    assert any(error["node"] == "extract_requirements_node" for error in state["errors"])
    assert state["shortlist"] == [{"job_id": "job-1", "final_score": 75}]


def test_workflow_persists_start_and_finish_metadata() -> None:
    repository = FakeWorkflowRepository()
    workflow = JobDiscoveryWorkflow(repository=cast(WorkflowRunRepository, repository))

    state = workflow.run({"run_id": "persisted-run", "source_name": "scheduled"})

    assert len(repository.saved_states) == 2
    assert repository.saved_states[0]["status"] == "running"
    assert repository.saved_states[-1]["status"] == "completed"
    assert repository.saved_states[-1]["source_name"] == "scheduled"
    assert repository.saved_states[-1]["completed_at"]
    assert repository.saved_states[-1]["history"]
    assert state["run_id"] == "persisted-run"
