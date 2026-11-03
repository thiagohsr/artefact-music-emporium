import time

import pytest

from emporio.agent.contract import AgentReply, ReplyDetails, Step
from emporio.chat.conversation import (
    CONVERSATION_LIMIT,
    FAILURE_ANSWER,
    MAX_MESSAGE_LENGTH,
    ConversationRegistry,
    answer_pending,
    new_conversation,
    submit,
    submit_edit,
)
from emporio.data.conversation_store import SESSION_LIMIT
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


def test_details_state_is_complete_for_full_details():
    reply = AgentReply("Resposta", ReplyDetails(model="qwen3:8b"))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=True)

    assert turn.details_state == "complete"


def test_details_state_is_incomplete_for_partial_details():
    reply = AgentReply("Resposta", ReplyDetails(complete=False))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=True)

    assert turn.details_state == "incomplete"


@pytest.mark.parametrize("details", [None, "not details", ReplyDetails(steps=("not a step",))])
def test_missing_or_malformed_details_do_not_block_the_answer(details):
    turn = answer(waiting_conversation(), ScriptedAgent(reply=AgentReply("Resposta", details)), keep_details=True)

    assert turn.outcome == "ok"
    assert turn.answer == "Resposta"
    assert turn.details is None
    assert turn.details_state == "unavailable"


def test_details_that_cannot_be_sanitized_are_unavailable():
    class Unprintable:
        def __str__(self):
            raise ValueError("cannot print")

    reply = AgentReply("Resposta", ReplyDetails(steps=(Step(name="passo", kind="tool", result=Unprintable()),)))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=True)

    assert turn.outcome == "ok"
    assert turn.details is None
    assert turn.details_state == "unavailable"


def test_failed_turn_gets_details_with_the_sanitized_error():
    turn = answer(
        waiting_conversation(),
        ScriptedAgent(error=RuntimeError(f"falhou com {PLANTED}")),
        keep_details=True,
    )

    assert "RuntimeError" in turn.details.errors[0]
    assert "falhou com" in turn.details.errors[0]
    assert PLANTED not in str(turn.details)
    assert turn.details_state == "incomplete"
    assert PLANTED not in turn.answer


def test_timed_out_turn_gets_details_recording_the_timeout():
    turn = answer(waiting_conversation(), ScriptedAgent(delay=0.2), timeout_seconds=0.01, keep_details=True)

    assert "timed out" in turn.details.errors[0]
    assert turn.details_state == "incomplete"


def test_blank_reply_keeps_the_details_the_agent_sent():
    step = Step(name="passo", kind="tool")
    reply = AgentReply("  ", ReplyDetails(steps=(step,)))

    turn = answer(waiting_conversation(), ScriptedAgent(reply=reply), keep_details=True)

    assert turn.outcome == "failed"
    assert turn.details.steps == (step,)
    assert "blank" in turn.details.errors[0]


def test_failed_turn_has_no_details_when_troubleshooting_is_off():
    turn = answer(waiting_conversation(), ScriptedAgent(error=RuntimeError("detalhe")), keep_details=False)

    assert turn.details is None
    assert turn.details_state == "unavailable"


def test_on_wait_reports_growing_elapsed_seconds_while_the_agent_runs():
    seen = []

    answer_pending(
        waiting_conversation(),
        ScriptedAgent(delay=0.25),
        Sanitizer(),
        timeout_seconds=2,
        keep_details=False,
        on_wait=seen.append,
    )

    assert len(seen) >= 2
    assert seen == sorted(seen)
    assert seen[0] >= 0


def test_interrupted_wait_resumes_without_calling_the_agent_again():
    class Interrupted(BaseException):
        """Streamlit stops a script with an exception like this when a rerun is requested."""

    def interrupt(_elapsed):
        raise Interrupted

    conversation = waiting_conversation()
    agent = ScriptedAgent(delay=0.2)

    with pytest.raises(Interrupted):
        answer_pending(
            conversation,
            agent,
            Sanitizer(),
            timeout_seconds=2,
            keep_details=False,
            on_wait=interrupt,
        )
    assert conversation.state == "waiting"

    turn = answer(conversation, agent)

    assert len(agent.calls) == 1
    assert turn.outcome == "ok"
    assert conversation.state == "idle"


def test_resumed_wait_keeps_counting_from_the_first_call():
    class Interrupted(BaseException):
        pass

    def interrupt(_elapsed):
        raise Interrupted

    conversation = waiting_conversation()
    agent = ScriptedAgent(delay=0.3)
    with pytest.raises(Interrupted):
        answer_pending(
            conversation,
            agent,
            Sanitizer(),
            timeout_seconds=0.1,
            keep_details=False,
            on_wait=interrupt,
        )
    time.sleep(0.15)

    turn = answer(conversation, agent, timeout_seconds=0.1)

    assert turn.outcome == "timed_out"
    assert turn.elapsed_ms >= 100


def test_blank_edit_closes_the_panel():
    conversation = new_conversation()
    submit(conversation, "a" * (MAX_MESSAGE_LENGTH + 1))

    assert submit_edit(conversation, "   ") == "blank"
    assert conversation.rejected_draft is None
    assert conversation.turns == []


def test_edit_with_text_works_like_a_message():
    conversation = new_conversation()
    submit(conversation, "a" * (MAX_MESSAGE_LENGTH + 1))

    assert submit_edit(conversation, "curta") == "accepted"
    assert conversation.turns[0].message == "curta"


def test_the_registry_finds_a_conversation_until_its_limit():
    registry = ConversationRegistry()
    conversation = registry.start()

    assert registry.find(conversation.id) is conversation
    conversation.last_message_at -= CONVERSATION_LIMIT

    assert registry.find(conversation.id) is None


def test_the_registry_finds_nothing_without_a_known_link():
    registry = ConversationRegistry()
    registry.start()

    assert registry.find(None) is None
    assert registry.find("inventado") is None


def test_a_removed_conversation_cannot_be_found():
    registry = ConversationRegistry()
    conversation = registry.start()

    registry.remove(conversation.id)

    assert registry.find(conversation.id) is None


def test_a_message_keeps_a_conversation_within_its_limit():
    registry = ConversationRegistry()
    conversation = registry.start()
    conversation.last_message_at -= CONVERSATION_LIMIT

    assert submit(conversation, "Olá") == "accepted"

    assert registry.find(conversation.id) is conversation


def test_the_page_limit_matches_the_agents_session_limit():
    assert CONVERSATION_LIMIT == SESSION_LIMIT
