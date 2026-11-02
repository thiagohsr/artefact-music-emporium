import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Literal

from emporio.agent.contract import Agent, AgentReply, ReplyDetails, is_valid_details
from emporio.errors import EmporioError
from emporio.safety.sanitize import Sanitizer

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
WAIT_TICK_SECONDS = 0.1
FAILURE_ANSWER = (
    "Desculpe, não consegui responder agora. Tente novamente ou fale com a gente pelo WhatsApp "
    "(67) 3341-4444 ou (67) 3321-4500, ou pelo e-mail contato@emporiodamusica.com.br."
)

Outcome = Literal["ok", "failed", "timed_out"]
SubmitResult = Literal["accepted", "blank", "too_long", "busy"]
DetailsState = Literal["complete", "incomplete", "unavailable"]


@dataclass
class Turn:
    message: str
    answer: str = ""
    outcome: Outcome | None = None
    elapsed_ms: float = 0
    details: ReplyDetails | None = None
    details_state: DetailsState = "unavailable"


@dataclass
class Conversation:
    id: str
    turns: list[Turn] = field(default_factory=list)
    state: Literal["idle", "waiting"] = "idle"
    rejected_draft: str | None = None
    pending_call: "_PendingCall | None" = None


def new_conversation() -> Conversation:
    return Conversation(id=uuid.uuid4().hex)


def submit(conversation: Conversation, text: str) -> SubmitResult:
    if conversation.state != "idle":
        return "busy"
    message = text.strip()
    if not message:
        return "blank"
    if len(message) > MAX_MESSAGE_LENGTH:
        conversation.rejected_draft = text
        return "too_long"
    conversation.rejected_draft = None
    conversation.turns.append(Turn(message=message))
    conversation.state = "waiting"
    return "accepted"


def submit_edit(conversation: Conversation, text: str) -> SubmitResult:
    """Clearing the text in the long-message panel means giving up on it, unlike a blank chat input."""
    result = submit(conversation, text)
    if result == "blank":
        conversation.rejected_draft = None
    return result


class _PendingCall:
    """Outlives a Streamlit rerun, so a rerun resumes instead of calling again."""

    def __init__(self, agent: Agent, conversation_id: str, message: str) -> None:
        self.started = time.monotonic()
        self._results: list[tuple[Outcome, object]] = []

        def call() -> None:
            try:
                self._results.append(("ok", agent.respond(conversation_id, message)))
            except EmporioError as error:
                self._results.append(("failed", error))
            except Exception as error:  # noqa: BLE001 - the contract lets an agent raise anything
                self._results.append(("failed", error))

        # A daemon thread, because a running call cannot be interrupted.
        self._thread = threading.Thread(target=call, daemon=True)
        self._thread.start()

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started

    def wait(self, timeout_seconds: float, on_wait: Callable[[float], None] | None) -> tuple[Outcome, object]:
        while self._thread.is_alive():
            remaining = timeout_seconds - self.elapsed_seconds()
            if remaining <= 0:
                break
            if on_wait is not None:
                on_wait(self.elapsed_seconds())
            self._thread.join(min(WAIT_TICK_SECONDS, remaining))
        if self._results:
            return self._results[0]
        return ("timed_out", None) if self._thread.is_alive() else ("failed", None)


def _is_usable(reply: object) -> bool:
    return isinstance(reply, AgentReply) and isinstance(reply.answer, str) and bool(reply.answer.strip())


def _describe_failure(outcome: Outcome, result: object) -> str:
    if outcome == "timed_out":
        return "The agent timed out before replying."
    if isinstance(result, Exception):
        return f"{type(result).__name__}: {result}"
    if result is None:
        return "The agent call ended with no result."
    return "The agent returned a blank or invalid reply."


def _log_failure(outcome: Outcome, result: object, sanitizer: Sanitizer) -> None:
    if outcome == "timed_out":
        logger.warning(_describe_failure(outcome, result))
    elif isinstance(result, EmporioError):
        logger.error("Agent failure: %s", sanitizer.text(_describe_failure(outcome, result)))
    elif isinstance(result, Exception):
        logger.error("Unexpected agent failure:\n%s", sanitizer.exception(result))
    else:
        logger.error(_describe_failure(outcome, result))


def _build_details(outcome: Outcome, result: object, sanitizer: Sanitizer) -> tuple[ReplyDetails | None, DetailsState]:
    """Every failure gets details from the chat, because the agent may not have returned any."""
    details = getattr(result, "details", None)
    if not is_valid_details(details):
        details = None
    try:
        if outcome != "ok":
            base = details or ReplyDetails()
            error = _describe_failure(outcome, result)
            details = replace(base, errors=(*base.errors, error), complete=False)
        if details is None:
            return None, "unavailable"
        return sanitizer.clean(details), "complete" if details.complete else "incomplete"
    except Exception as error:  # noqa: BLE001 - bad details must not block the answer
        logger.error("Reply details became unavailable:\n%s", sanitizer.exception(error))
        return None, "unavailable"


def answer_pending(
    conversation: Conversation,
    agent: Agent,
    sanitizer: Sanitizer,
    *,
    timeout_seconds: float,
    keep_details: bool,
    on_wait: Callable[[float], None] | None = None,
) -> Turn:
    turn = conversation.turns[-1]
    if conversation.pending_call is None:
        conversation.pending_call = _PendingCall(agent, conversation.id, turn.message)
    pending = conversation.pending_call
    outcome, result = pending.wait(timeout_seconds, on_wait)
    turn.elapsed_ms = pending.elapsed_seconds() * 1000
    conversation.pending_call = None

    if outcome == "ok" and not _is_usable(result):
        outcome = "failed"
    if outcome != "ok":
        _log_failure(outcome, result, sanitizer)
    turn.outcome = outcome
    turn.answer = sanitizer.text(result.answer) if outcome == "ok" else FAILURE_ANSWER
    if keep_details:
        turn.details, turn.details_state = _build_details(outcome, result, sanitizer)

    conversation.state = "idle"
    return turn
