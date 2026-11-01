import subprocess
import sys
import textwrap

import pytest

from emporio.agent.contract import AgentReply, ReplyDetails, is_valid_details
from emporio.agent.stand_in import FAKE_API_KEY, StandInAgent

CONVERSATION_ID = "conversation-1"


@pytest.fixture
def agent():
    return StandInAgent(slow_seconds=0.01)


def test_importing_the_agent_package_does_not_load_streamlit():
    script = textwrap.dedent(
        """
        import importlib
        import pkgutil
        import sys

        import emporio.agent

        for module in pkgutil.iter_modules(emporio.agent.__path__):
            importlib.import_module(f"emporio.agent.{module.name}")

        sys.exit("streamlit" in sys.modules)
        """
    )
    assert subprocess.run([sys.executable, "-c", script]).returncode == 0


def test_stand_in_is_marked_as_simulated(agent):
    assert agent.is_simulated is True
    assert agent.name


@pytest.mark.parametrize(
    "message",
    [
        "Olá",
        "/ferramenta",
        "/politica",
        "/fallback",
        "/raciocinio",
        "/grande",
        "/incompleto",
        "/sensivel",
        "/lento",
    ],
)
def test_each_command_returns_a_valid_reply(agent, message):
    reply = agent.respond(CONVERSATION_ID, message)

    assert isinstance(reply, AgentReply)
    assert reply.answer.strip()
    assert is_valid_details(reply.details)


@pytest.mark.parametrize(
    "message",
    ["Olá", "/ferramenta", "/politica", "/fallback", "/raciocinio", "/grande", "/incompleto", "/sem-detalhes"],
)
def test_same_input_gives_same_output(agent, message):
    assert agent.respond(CONVERSATION_ID, message) == agent.respond(CONVERSATION_ID, message)


def test_simple_reply_has_no_steps_or_sources(agent):
    details = agent.respond(CONVERSATION_ID, "Olá").details

    assert details.steps == ()
    assert details.sources == ()
    assert details.complete is True


def test_ferramenta_uses_a_tool_and_a_data_source(agent):
    details = agent.respond(CONVERSATION_ID, "/ferramenta").details

    assert [step.kind for step in details.steps] == ["tool"]
    assert details.steps[0].inputs
    assert details.steps[0].result
    assert [source.kind for source in details.sources] == ["data"]


def test_politica_uses_retrieval_and_a_policy_source(agent):
    details = agent.respond(CONVERSATION_ID, "/politica").details

    assert [step.kind for step in details.steps] == ["retrieval"]
    assert [source.kind for source in details.sources] == ["policy"]


def test_fallback_is_reported(agent):
    assert agent.respond(CONVERSATION_ID, "/fallback").details.fallback_used is True


def test_raciocinio_includes_a_reasoning_step(agent):
    assert agent.respond(CONVERSATION_ID, "/raciocinio").details.steps[0].kind == "reasoning"


def test_grande_exceeds_the_large_details_limits(agent):
    steps = agent.respond(CONVERSATION_ID, "/grande").details.steps

    assert len(steps) > 10
    assert any(len(str(step.result)) > 2000 for step in steps)


def test_incompleto_marks_details_as_partial(agent):
    assert agent.respond(CONVERSATION_ID, "/incompleto").details.complete is False


def test_sem_detalhes_returns_no_details(agent):
    assert agent.respond(CONVERSATION_ID, "/sem-detalhes").details is None


def test_sensivel_plants_the_fake_key_in_a_result_and_an_error(agent):
    step = agent.respond(CONVERSATION_ID, "/sensivel").details.steps[0]

    assert FAKE_API_KEY in str(step.result)
    assert FAKE_API_KEY in step.error


def test_erro_raises(agent):
    with pytest.raises(RuntimeError):
        agent.respond(CONVERSATION_ID, "/erro")


def test_a_command_must_be_the_whole_first_word(agent):
    assert agent.respond(CONVERSATION_ID, "/errors").details.steps == ()


@pytest.mark.parametrize(
    "details",
    [
        None,
        "not details",
        ReplyDetails(steps=("not a step",)),
        ReplyDetails(sources=("not a source",)),
        ReplyDetails(errors=(1,)),
    ],
)
def test_invalid_details_are_recognized(details):
    assert is_valid_details(details) is False
