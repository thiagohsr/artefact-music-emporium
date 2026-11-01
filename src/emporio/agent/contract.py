from dataclasses import dataclass
from typing import Any, Literal, Protocol, get_args

StepKind = Literal["tool", "retrieval", "model", "reasoning"]
StepStatus = Literal["ok", "error"]
SourceKind = Literal["data", "policy", "other"]


@dataclass(frozen=True)
class Step:
    name: str
    kind: StepKind
    status: StepStatus = "ok"
    duration_ms: float | None = None
    inputs: Any = None
    result: Any = None
    error: str | None = None


@dataclass(frozen=True)
class Source:
    kind: SourceKind
    name: str


@dataclass(frozen=True)
class ReplyDetails:
    steps: tuple[Step, ...] = ()
    sources: tuple[Source, ...] = ()
    model: str | None = None
    provider: str | None = None
    fallback_used: bool = False
    errors: tuple[str, ...] = ()
    complete: bool = True


@dataclass(frozen=True)
class AgentReply:
    answer: str
    details: ReplyDetails | None = None


class Agent(Protocol):
    name: str
    is_simulated: bool

    def respond(self, conversation_id: str, message: str) -> AgentReply: ...


def _is_valid_step(step: Any) -> bool:
    return (
        isinstance(step, Step)
        and bool(step.name)
        and step.kind in get_args(StepKind)
        and step.status in get_args(StepStatus)
        and (step.duration_ms is None or step.duration_ms >= 0)
    )


def _is_valid_source(source: Any) -> bool:
    return isinstance(source, Source) and bool(source.name) and source.kind in get_args(SourceKind)


def is_valid_details(details: Any) -> bool:
    """Invalid details must not block an answer, so they are checked here instead of raising."""
    try:
        return (
            isinstance(details, ReplyDetails)
            and all(_is_valid_step(step) for step in details.steps)
            and all(_is_valid_source(source) for source in details.sources)
            and all(isinstance(error, str) for error in details.errors)
        )
    except TypeError:
        return False
