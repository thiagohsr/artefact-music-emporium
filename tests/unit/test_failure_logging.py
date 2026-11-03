import logging

import pytest

from emporio.agent.contract import AgentReply, ReplyDetails, Step
from emporio.agent.factory import AGENTS, create_agent
from emporio.chat.conversation import (
    FAILURE_ANSWER,
    answer_pending,
    new_conversation,
    submit,
)
from emporio.config import Settings
from emporio.errors import ConfigError, ProviderError
from emporio.safety.sanitize import Sanitizer

PLANTED = "planted-private-value"


class Raising:
    def __init__(self, error):
        self.error = error

    def respond(self, conversation_id, message):
        raise self.error


def run(agent, *, timeout_seconds=5, keep_details=False):
    conversation = new_conversation()
    submit(conversation, "Olá")
    return answer_pending(
        conversation,
        agent,
        Sanitizer([PLANTED]),
        timeout_seconds=timeout_seconds,
        keep_details=keep_details,
    )


def logged(caplog):
    return "\n".join(record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("error", [RuntimeError(f"falhou com {PLANTED}"), ProviderError(f"falhou com {PLANTED}")])
def test_agent_failure_is_logged_without_secrets_and_the_customer_sees_the_friendly_text(caplog, error):
    with caplog.at_level(logging.ERROR, logger="emporio"):
        turn = run(Raising(error))

    assert turn.answer == FAILURE_ANSWER
    assert type(error).__name__ in logged(caplog)
    assert "falhou com" in logged(caplog)
    assert PLANTED not in logged(caplog)
    assert PLANTED not in caplog.text


def test_unexpected_failure_logs_its_traceback(caplog):
    with caplog.at_level(logging.ERROR, logger="emporio"):
        run(Raising(RuntimeError("inesperado")))

    assert "Traceback" in logged(caplog)


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_call_that_ends_with_no_result_is_a_failure_and_is_logged(caplog):
    with caplog.at_level(logging.ERROR, logger="emporio"):
        turn = run(Raising(SystemExit(1)))

    assert turn.outcome == "failed"
    assert "no result" in logged(caplog)


def test_timeout_is_logged(caplog):
    class Slow:
        def respond(self, conversation_id, message):
            import time

            time.sleep(0.2)

    with caplog.at_level(logging.WARNING, logger="emporio"):
        turn = run(Slow(), timeout_seconds=0.01)

    assert turn.outcome == "timed_out"
    assert "timed out" in logged(caplog)


def test_details_that_become_unavailable_are_logged(caplog):
    class Unprintable:
        def __str__(self):
            raise ValueError("cannot print")

    class Agent:
        def respond(self, conversation_id, message):
            return AgentReply("Resposta", ReplyDetails(steps=(Step("passo", "tool", result=Unprintable()),)))

    with caplog.at_level(logging.ERROR, logger="emporio"):
        turn = run(Agent(), keep_details=True)

    assert turn.details_state == "unavailable"
    assert turn.outcome == "ok"
    assert "details" in logged(caplog)


def test_agent_that_cannot_start_logs_the_cause_and_the_error_shows_none(caplog, monkeypatch):
    monkeypatch.setenv("MY_API_KEY", PLANTED)

    def fail(_settings):
        raise RuntimeError(f"startup failed with {PLANTED}")

    monkeypatch.setitem(AGENTS, "broken", fail)

    with caplog.at_level(logging.ERROR, logger="emporio"), pytest.raises(ConfigError) as error:
        create_agent(Settings(agent="broken", troubleshooting=False, reply_timeout_seconds=60))

    assert "startup failed" not in str(error.value)
    assert "startup failed" in logged(caplog)
    assert PLANTED not in logged(caplog)
