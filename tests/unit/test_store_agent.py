import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from pydantic_ai import Tool
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from emporio.agent.store.agent import TOOLS, StoreAgent, clean_answer
from emporio.data.conversation_store import SessionStore


def user_texts(messages):
    return [p.content for m in messages for p in m.parts if isinstance(p, UserPromptPart)]


def echo_history(messages, _info):
    return ModelResponse(parts=[TextPart(" | ".join(user_texts(messages)))])


def build(function=echo_history, *, limit=30.0, tools=(), sessions=None):
    return StoreAgent(
        FunctionModel(function),
        primary_model="function",
        settings={},
        reply_timeout_seconds=limit,
        tools=tools,
        sessions=sessions,
    )


def test_respond_works_from_new_threads_one_after_another():
    agent = build()
    answers = []
    for message in ("primeira", "segunda"):
        thread = threading.Thread(target=lambda m=message: answers.append(agent.respond("c1", m).answer))
        thread.start()
        thread.join(10)

    assert answers == ["primeira", "primeira | segunda"]


def test_respond_works_from_threads_at_the_same_time():
    agent = build()
    answers = {}
    threads = [
        threading.Thread(target=lambda i=i: answers.update({i: agent.respond(f"c{i}", f"m{i}").answer})) for i in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert answers == {i: f"m{i}" for i in range(4)}


def test_history_stays_within_its_conversation():
    agent = build()
    agent.respond("c1", "um")
    agent.respond("c2", "outra")

    assert agent.respond("c1", "dois").answer == "um | dois"


def test_session_older_than_the_limit_starts_fresh():
    moment = [datetime(2026, 11, 2, 10, tzinfo=UTC)]
    agent = build(sessions=SessionStore(clock=lambda: moment[0]))
    agent.respond("c1", "antes")

    moment[0] += timedelta(minutes=29)
    assert agent.respond("c1", "ainda").answer == "antes | ainda"

    moment[0] += timedelta(minutes=30)
    assert agent.respond("c1", "depois").answer == "depois"


def test_end_conversation_starts_fresh_and_accepts_an_unknown_id():
    agent = build()
    agent.respond("c1", "antes")

    agent.end_conversation("c1")
    agent.end_conversation("unknown")

    assert agent.respond("c1", "depois").answer == "depois"


def test_run_past_its_limit_raises_and_saves_no_history():
    async def slow_once(messages, _info):
        if user_texts(messages)[-1] == "lento":
            await asyncio.sleep(1)
        return echo_history(messages, _info)

    agent = build(slow_once, limit=0.2)
    with pytest.raises(TimeoutError):
        agent.respond("c1", "lento")

    assert agent.respond("c1", "rápido").answer == "rápido"


def test_synchronous_tools_do_not_block_the_event_loop():
    def wait_a_bit() -> str:
        time.sleep(0.4)
        return "ok"

    def call_then_answer(messages, _info):
        if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            return ModelResponse(parts=[TextPart("fim")])
        return ModelResponse(parts=[ToolCallPart("wait_a_bit", {})])

    agent = build(call_then_answer, tools=[Tool(wait_a_bit)])
    threads = [threading.Thread(target=lambda i=i: agent.respond(f"c{i}", "oi")) for i in range(3)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert time.monotonic() - started < 1.0


def test_details_come_from_this_run_only():
    def call_once(messages, _info):
        if user_texts(messages)[-1] == "usa" and not any(isinstance(p, ToolReturnPart) for p in messages[-1].parts):
            return ModelResponse(parts=[ToolCallPart("noop", {})])
        return ModelResponse(parts=[TextPart("ok")])

    def noop() -> str:
        return "ok"

    agent = build(call_once, tools=[Tool(noop)])
    assert [s.name for s in agent.respond("c1", "usa").details.steps] == ["noop"]
    assert agent.respond("c1", "oi").details.steps == ()


def test_payment_terms_requires_the_number_of_installments():
    schema = {tool.name: tool.function_schema.json_schema for tool in TOOLS}["payment_terms"]

    assert "installments" in schema["required"]
    assert "method" not in schema["required"]


@pytest.mark.parametrize(
    ("answer", "cleaned"),
    [
        ("Até logo!", "Até logo!"),
        ("Até logo!\n\n finish_conversation", "Até logo!"),
        ('Até logo! <function_call> {"name": "finish_conversation"} </function_call>', "Até logo!"),
        ('Até logo! <function_call> {"name": "x"}', "Até logo!"),
        ("Use o get_product mais tarde", "Use o get_product mais tarde"),
        ('registar_reclamacao\n{"name": "register_complaint", "arguments": {"summary": "x"}}', ""),
    ],
)
def test_clean_answer_removes_tool_calls_written_as_text(answer, cleaned):
    assert clean_answer(answer) == cleaned

