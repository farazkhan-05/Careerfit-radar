from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, NotRequired, TypedDict, cast

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.db_models import WorkflowRun


class WorkflowError(RuntimeError):
    pass


class JobDiscoveryState(TypedDict):
    run_id: str
    status: str
    started_at: str
    source_name: NotRequired[str | None]
    search: NotRequired[dict[str, Any]]
    completed_at: NotRequired[str | None]
    preferences: NotRequired[dict[str, Any]]
    source_results: NotRequired[list[dict[str, Any]]]
    normalized_jobs: NotRequired[list[dict[str, Any]]]
    accepted_jobs: NotRequired[list[dict[str, Any]]]
    rejected_jobs: NotRequired[list[dict[str, Any]]]
    canonical_jobs: NotRequired[list[dict[str, Any]]]
    duplicate_jobs: NotRequired[list[dict[str, Any]]]
    requirements: NotRequired[list[dict[str, Any]]]
    embeddings: NotRequired[list[dict[str, Any]]]
    stored_jobs: NotRequired[list[dict[str, Any]]]
    scores: NotRequired[list[dict[str, Any]]]
    gap_analyses: NotRequired[list[dict[str, Any]]]
    shortlist: NotRequired[list[dict[str, Any]]]
    history: NotRequired[list[dict[str, Any]]]
    errors: NotRequired[list[dict[str, Any]]]


StateProcessor = Callable[[JobDiscoveryState], Mapping[str, Any] | Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class WorkflowNodeConfig:
    minimum_shortlist_score: int = 70
    shortlist_limit: int = 25


@dataclass
class JobDiscoveryWorkflowDependencies:
    load_preferences: Callable[[], Mapping[str, Any]] = field(default=lambda: {})
    fetch_sources: StateProcessor = field(default=lambda state: [])
    normalise_jobs: StateProcessor = field(
        default=lambda state: state.get("normalized_jobs", [])
    )
    hard_filter: StateProcessor = field(
        default=lambda state: {
            "accepted_jobs": state.get("normalized_jobs", []),
            "rejected_jobs": [],
        }
    )
    deduplicate_jobs: StateProcessor = field(
        default=lambda state: {
            "canonical_jobs": state.get("accepted_jobs", []),
            "duplicate_jobs": [],
        }
    )
    extract_requirements: StateProcessor = field(default=lambda state: [])
    embed_jobs: StateProcessor = field(default=lambda state: [])
    store_jobs: StateProcessor = field(
        default=lambda state: state.get("canonical_jobs", [])
    )
    score_jobs: StateProcessor = field(default=lambda state: [])
    gap_analysis: StateProcessor = field(default=lambda state: [])


class WorkflowRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_state(self, state: JobDiscoveryState) -> WorkflowRun:
        existing = self._session.execute(
            select(WorkflowRun).where(WorkflowRun.run_id == state["run_id"])
        ).scalar_one_or_none()
        if existing is None:
            existing = WorkflowRun(
                run_id=state["run_id"],
                source_name=state.get("source_name"),
                status=state["status"],
                started_at=_parse_datetime(state["started_at"]),
                completed_at=_parse_optional_datetime(state.get("completed_at")),
                state=_json_ready(state),
                errors=state.get("errors", []),
            )
            self._session.add(existing)
        else:
            existing.source_name = state.get("source_name")
            existing.status = state["status"]
            existing.completed_at = _parse_optional_datetime(state.get("completed_at"))
            existing.state = _json_ready(state)
            existing.errors = state.get("errors", [])
        self._session.flush()
        return existing

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._session.execute(
            select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        ).scalar_one_or_none()

    def list_runs(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[WorkflowRun, ...]:
        statement = select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(limit)
        if status is not None:
            statement = statement.where(WorkflowRun.status == status)
        return tuple(self._session.execute(statement).scalars().all())


class JobDiscoveryWorkflow:
    def __init__(
        self,
        *,
        dependencies: JobDiscoveryWorkflowDependencies | None = None,
        repository: WorkflowRunRepository | None = None,
        config: WorkflowNodeConfig | None = None,
    ) -> None:
        self._dependencies = dependencies or JobDiscoveryWorkflowDependencies()
        self._repository = repository
        self._config = config or WorkflowNodeConfig()
        self.graph = build_job_discovery_graph(self)

    def run(self, initial_state: Mapping[str, Any] | None = None) -> JobDiscoveryState:
        state = create_initial_state(initial_state)
        return cast(JobDiscoveryState, self.graph.invoke(state))

    def persist_state(self, state: JobDiscoveryState) -> None:
        if self._repository is not None:
            self._repository.save_state(state)

    def start_run_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        updated = _record_event({**state, "status": "running"}, "start_run_node")
        self.persist_state(updated)
        return updated

    def load_preferences_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        try:
            preferences = dict(self._dependencies.load_preferences())
            return _record_event({**state, "preferences": preferences}, "load_preferences_node")
        except Exception as exc:
            return error_handler_node(state, "load_preferences_node", exc)

    def fetch_sources_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        try:
            results = [_json_ready(item) for item in self._dependencies.fetch_sources(state)]
            errors = list(state.get("errors", []))
            for result in results:
                if isinstance(result, dict) and result.get("status") == "failed":
                    errors.append(
                        {
                            "node": "fetch_sources_node",
                            "source": result.get("source_name"),
                            "message": result.get("error_message", "Source failed."),
                            "timestamp": _utc_now(),
                        }
                    )
            return _record_event(
                {**state, "source_results": results, "errors": errors},
                "fetch_sources_node",
                {"source_count": len(results), "source_failures": len(errors) - len(state.get("errors", []))},
            )
        except Exception as exc:
            return error_handler_node(state, "fetch_sources_node", exc)

    def normalise_jobs_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "normalise_jobs_node",
            "normalized_jobs",
            self._dependencies.normalise_jobs,
        )

    def hard_filter_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        try:
            output = _as_mapping(self._dependencies.hard_filter(state))
            accepted_jobs = [_json_ready(item) for item in output.get("accepted_jobs", [])]
            rejected_jobs = [_json_ready(item) for item in output.get("rejected_jobs", [])]
            return _record_event(
                {**state, "accepted_jobs": accepted_jobs, "rejected_jobs": rejected_jobs},
                "hard_filter_node",
                {"accepted": len(accepted_jobs), "rejected": len(rejected_jobs)},
            )
        except Exception as exc:
            return error_handler_node(state, "hard_filter_node", exc)

    def deduplicate_jobs_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        try:
            output = _as_mapping(self._dependencies.deduplicate_jobs(state))
            canonical_jobs = [_json_ready(item) for item in output.get("canonical_jobs", [])]
            duplicate_jobs = [_json_ready(item) for item in output.get("duplicate_jobs", [])]
            return _record_event(
                {**state, "canonical_jobs": canonical_jobs, "duplicate_jobs": duplicate_jobs},
                "deduplicate_jobs_node",
                {"canonical": len(canonical_jobs), "duplicates": len(duplicate_jobs)},
            )
        except Exception as exc:
            return error_handler_node(state, "deduplicate_jobs_node", exc)

    def extract_requirements_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "extract_requirements_node",
            "requirements",
            self._dependencies.extract_requirements,
        )

    def embed_jobs_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "embed_jobs_node",
            "embeddings",
            self._dependencies.embed_jobs,
        )

    def store_jobs_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "store_jobs_node",
            "stored_jobs",
            self._dependencies.store_jobs,
        )

    def score_jobs_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "score_jobs_node",
            "scores",
            self._dependencies.score_jobs,
        )

    def gap_analysis_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        return _processor_node(
            state,
            "gap_analysis_node",
            "gap_analyses",
            self._dependencies.gap_analysis,
        )

    def build_shortlist_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        scores = [dict(item) for item in state.get("scores", [])]
        shortlist = [
            score
            for score in sorted(
                scores,
                key=lambda item: int(item.get("final_score", 0)),
                reverse=True,
            )
            if int(score.get("final_score", 0)) >= self._config.minimum_shortlist_score
        ][: self._config.shortlist_limit]
        return _record_event(
            {**state, "shortlist": shortlist},
            "build_shortlist_node",
            {"shortlist_count": len(shortlist)},
        )

    def finish_run_node(self, state: JobDiscoveryState) -> JobDiscoveryState:
        status = "completed_with_errors" if state.get("errors") else "completed"
        updated = _record_event(
            {**state, "status": status, "completed_at": _utc_now()},
            "finish_run_node",
        )
        self.persist_state(updated)
        return updated


def build_job_discovery_graph(workflow: JobDiscoveryWorkflow) -> Any:
    graph = StateGraph(JobDiscoveryState)
    graph.add_node("start_run_node", workflow.start_run_node)
    graph.add_node("load_preferences_node", workflow.load_preferences_node)
    graph.add_node("fetch_sources_node", workflow.fetch_sources_node)
    graph.add_node("normalise_jobs_node", workflow.normalise_jobs_node)
    graph.add_node("hard_filter_node", workflow.hard_filter_node)
    graph.add_node("deduplicate_jobs_node", workflow.deduplicate_jobs_node)
    graph.add_node("extract_requirements_node", workflow.extract_requirements_node)
    graph.add_node("embed_jobs_node", workflow.embed_jobs_node)
    graph.add_node("store_jobs_node", workflow.store_jobs_node)
    graph.add_node("score_jobs_node", workflow.score_jobs_node)
    graph.add_node("gap_analysis_node", workflow.gap_analysis_node)
    graph.add_node("build_shortlist_node", workflow.build_shortlist_node)
    graph.add_node("finish_run_node", workflow.finish_run_node)
    graph.add_node("error_handler_node", lambda state: error_handler_node(state))

    graph.set_entry_point("start_run_node")
    graph.add_edge("start_run_node", "load_preferences_node")
    graph.add_edge("load_preferences_node", "fetch_sources_node")
    graph.add_edge("fetch_sources_node", "normalise_jobs_node")
    graph.add_edge("normalise_jobs_node", "hard_filter_node")
    graph.add_edge("hard_filter_node", "deduplicate_jobs_node")
    graph.add_edge("deduplicate_jobs_node", "extract_requirements_node")
    graph.add_edge("extract_requirements_node", "embed_jobs_node")
    graph.add_edge("embed_jobs_node", "store_jobs_node")
    graph.add_edge("store_jobs_node", "score_jobs_node")
    graph.add_edge("score_jobs_node", "gap_analysis_node")
    graph.add_edge("gap_analysis_node", "build_shortlist_node")
    graph.add_edge("build_shortlist_node", "finish_run_node")
    graph.add_edge("finish_run_node", END)
    return graph.compile()


def create_initial_state(initial_state: Mapping[str, Any] | None = None) -> JobDiscoveryState:
    values = dict(initial_state or {})
    started_at = str(values.get("started_at") or _utc_now())
    state: JobDiscoveryState = {
        "run_id": str(values.get("run_id") or uuid.uuid4()),
        "source_name": cast(str | None, values.get("source_name")),
        "status": str(values.get("status") or "pending"),
        "started_at": started_at,
        "history": list(values.get("history", [])),
        "errors": list(values.get("errors", [])),
    }
    if isinstance(values.get("search"), Mapping):
        state["search"] = dict(cast(Mapping[str, Any], values["search"]))
    return state


def error_handler_node(
    state: JobDiscoveryState,
    node_name: str = "error_handler_node",
    error: Exception | None = None,
) -> JobDiscoveryState:
    errors = list(state.get("errors", []))
    if error is not None:
        errors.append(
            {
                "node": node_name,
                "message": str(error),
                "timestamp": _utc_now(),
            }
        )
    return _record_event({**state, "errors": errors, "status": "running"}, "error_handler_node")


def _processor_node(
    state: JobDiscoveryState,
    node_name: str,
    output_key: str,
    processor: StateProcessor,
) -> JobDiscoveryState:
    try:
        output = processor(state)
        items: Iterable[Any]
        if isinstance(output, Mapping):
            raw = output.get(output_key, output.get("items", []))
            items = cast(Iterable[Any], raw)
        else:
            items = output
        values = [_json_ready(item) for item in items]
        updated = cast(JobDiscoveryState, {**state, output_key: values})
        return _record_event(updated, node_name, {"count": len(values)})
    except Exception as exc:
        return error_handler_node(state, node_name, exc)


def _as_mapping(value: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkflowError("Workflow dependency must return a mapping for this node.")
    return value


def _record_event(
    state: JobDiscoveryState,
    node_name: str,
    metadata: Mapping[str, Any] | None = None,
) -> JobDiscoveryState:
    history = list(state.get("history", []))
    history.append(
        {
            "node": node_name,
            "status": state.get("status", "running"),
            "timestamp": _utc_now(),
            "metadata": dict(metadata or {}),
        }
    )
    return {**state, "history": history}


def _json_ready(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {
            key: _json_ready(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_ready(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(value)
