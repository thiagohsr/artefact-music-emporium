import time

import pytest

from emporio.agent.contract import AgentReply, ReplyDetails
from emporio.chat.conversation import (
    FAILURE_ANSWER,
    MAX_MESSAGE_LENGTH,
    answer_pending,
    new_conversation,
    submit,
)
from emporio.safety.sanitize import REDACTED, Sanitizer

PLANTED = "planted-private-value"


class ScriptedAgent:
    name = "scripted"
    is_simulated = True

    def __init__(self, reply=None, error=None, delay=0):
        self.reply = reply if reply is not None else AgentReply("Resposta")
        self.error = error
        self.delay = delay
        self.calls = []

    def respond(self, conversation_id, message):
        self.calls.append((conversation_id, message))
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


def answer(conversation, agent, timeout_seconds=2, keep_details=False):
    return answer_pending(
        conversation,
        agent,
        Sanitizer([PLANTED]),
        timeout_seconds=timeout_seconds,
        keep_details=keep_details,
    )


def waiting_conversation(message="Olá"):
    conversation = new_conversation()
    submit(conversation, message)
    return conversation


def test_new_conversations_get_unique_ids():
    assert new_conversation().id != new_conversation().id


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_blank_messages_are_rejected(text):
    conversation = new_conversation()

    assert submit(conversation, text) == "blank"
    assert conversation.turns == []
    assert conversation.state == "idle"
    assert conversation.rejected_draft is None


def test_message_is_trimmed_and_moves_to_waiting():
    conversation = new_conversation()

    assert submit(conversation, "  Olá  ") == "accepted"
    assert conversation.turns[0].message == "Olá"
    assert conversation.state == "waiting"


def test_message_at_the_limit_is_accepted():
    conversation = new_conversation()

    assert submit(conversation, "a" * MAX_MESSAGE_LENGTH) == "accepted"


def test_limit_applies_after_trimming():
    conversation = new_conversation()

    assert submit(conversation, " " + "a" * MAX_MESSAGE_LENGTH + " ") == "accepted"


def test_message_over_the_limit_is_kept_for_editing():
    conversation = new_conversation()
    text = "a" * (MAX_MESSAGE_LENGTH + 1)

    assert submit(conversation, text) == "too_long"
    assert conversation.rejected_draft == text
    assert conversation.turns == []
    assert conversation.state == "idle"


def test_accepted_message_clears_the_rejected_draft():
    conversation = new_conversation()
    submit(conversation, "a" * (MAX_MESSAGE_LENGTH + 1))

    submit(conversation, "Olá")

    assert conversation.rejected_draft is None


def test_only_idle_conversations_accept_messages():
    conversation = waiting_conversation()

    assert submit(conversation, "Outra") == "busy"
    assert len(conversation.turns) == 1


def test_answer_returns_to_idle_and_records_the_reply():
    conversation = waiting_conversation()
    agent = ScriptedAgent()

    turn = answer(conversation, agent)

    assert agent.calls == [(conversation.id, "Olá")]
    assert conversation.state == "idle"
    assert turn.answer == "Resposta"
    assert turn.outcome == "ok"
    assert turn.elapsed_ms >= 0


def test_exception_gives_the_failed_outcome():
    conversation = waiting_conversation()

    turn = answer(conversation, ScriptedAgent(error=RuntimeError("detalhe interno")))

    assert turn.outcome == "failed"
    assert turn.answer == FAILURE_ANSWER
    assert conversation.state == "idle"


@pytest.mark.parametrize("reply", [AgentReply(""), AgentReply("   "), "not a reply"])
def test_blank_or_invalid_reply_gives_the_failed_outcome(reply):
    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply))

    assert turn.outcome == "failed"
    assert turn.answer == FAILURE_ANSWER


def test_timeout_gives_timed_out_and_discards_the_late_result():
    conversation = waiting_conversation()

    turn = answer(conversation, ScriptedAgent(delay=0.2), timeout_seconds=0.01)

    assert turn.outcome == "timed_out"
    assert turn.answer == FAILURE_ANSWER
    assert conversation.state == "idle"
    time.sleep(0.3)
    assert turn.answer == FAILURE_ANSWER
    assert turn.outcome == "timed_out"


def test_answer_is_sanitized():
    turn = answer(waiting_conversation(), ScriptedAgent(reply=AgentReply(f"usando {PLANTED}")))

    assert PLANTED not in turn.answer
    assert REDACTED in turn.answer


def test_details_are_discarded_when_troubleshooting_is_off():
    reply = AgentReply("Resposta", ReplyDetails(model="qwen3:8b"))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=False)

    assert turn.details is None


def test_details_are_sanitized_when_kept():
    reply = AgentReply("Resposta", ReplyDetails(errors=(f"erro {PLANTED}",)))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=True)

    assert PLANTED not in str(turn.details)
