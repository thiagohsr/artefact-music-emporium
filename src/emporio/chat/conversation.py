import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Literal

from emporio.agent.contract import Agent, AgentReply, ReplyDetails, is_valid_details
from emporio.safety.sanitize import Sanitizer

MAX_MESSAGE_LENGTH = 2000
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


def _call_agent(agent: Agent, conversation_id: str, message: str, timeout_seconds: float) -> tuple[Outcome, object]:
    """Runs the call in a daemon thread, because a running call cannot be interrupted."""
    results: list[tuple[Outcome, object]] = []

    def call() -> None:
        try:
            results.append(("ok", agent.respond(conversation_id, message)))
        except Exception as error:
            results.append(("failed", error))

    thread = threading.Thread(target=call, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    return results[0] if results else ("timed_out", None)


def _is_usable(reply: object) -> bool:
    return isinstance(reply, AgentReply) and isinstance(reply.answer, str) and bool(reply.answer.strip())


def _describe_failure(outcome: Outcome, result: object) -> str:
    if outcome == "timed_out":
        return "The agent timed out before replying."
    if isinstance(result, Exception):
        return f"{type(result).__name__}: {result}"
    return "The agent returned a blank or invalid reply."


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
        return sanitizer.value(details), "complete" if details.complete else "incomplete"
    except Exception:
        return None, "unavailable"


def answer_pending(
    conversation: Conversation,
    agent: Agent,
    sanitizer: Sanitizer,
    *,
    timeout_seconds: float,
    keep_details: bool,
) -> Turn:
    turn = conversation.turns[-1]
    started = time.monotonic()
    outcome, result = _call_agent(agent, conversation.id, turn.message, timeout_seconds)
    turn.elapsed_ms = (time.monotonic() - started) * 1000

    if outcome == "ok" and not _is_usable(result):
        outcome = "failed"
    turn.outcome = outcome
    turn.answer = sanitizer.text(result.answer) if outcome == "ok" else FAILURE_ANSWER
    if keep_details:
        turn.details, turn.details_state = _build_details(outcome, result, sanitizer)

    conversation.state = "idle"
    return turn
