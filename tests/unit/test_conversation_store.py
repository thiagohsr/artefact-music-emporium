import json
import sqlite3
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic_ai import Tool
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from emporio.agent.store.agent import (
    StoreAgent,
    _find_open_conversation,
    _get_order_status,
)
from emporio.data.conversation_store import (
    SessionStore,
    close,
    find_open,
    known_values,
    save,
    serialize,
    user_id_for,
)
from emporio.errors import ProviderError

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
NAME, PHONE, EMAIL = "Ana Souza", "(67) 99123-4567", "ana.souza@example.com"


@pytest.fixture
def conn(store_conn):
    store_conn.row_factory = sqlite3.Row
    return store_conn


def messages(text=f"Sou {NAME}, {PHONE}, {EMAIL}"):
    return [
        ModelRequest(parts=[UserPromptPart(text)]),
        ModelResponse(parts=[ThinkingPart("pensando no cliente"), ToolCallPart("get_order_status", {"phone": PHONE, "email": EMAIL}, tool_call_id="1")]),
        ModelRequest(parts=[ToolReturnPart("get_order_status", {"customer_name": NAME}, tool_call_id="1")]),
        ModelResponse(parts=[TextPart(f"Olá, Ana! Seu e-mail é {EMAIL}.")]),
    ]


KNOWN = (NAME, "Ana", "Souza", PHONE, EMAIL)


def test_user_id_is_stable_and_not_the_customer_id(conn):
    first = user_id_for(conn, 1)

    assert first == user_id_for(conn, 1)
    assert first != user_id_for(conn, 2)
    assert first != "1"


def test_stored_messages_have_no_readable_personal_data_or_thinking():
    stored = serialize(messages(), KNOWN)

    json.loads(stored)
    for private in (NAME, "Ana", "Souza", "99123", EMAIL, "pensando"):
        assert private not in stored


def test_masking_keeps_words_that_only_contain_a_name():
    assert "Banana" in serialize([ModelRequest(parts=[UserPromptPart("Banana")])], KNOWN)


def test_known_values_include_the_name_parts_and_contacts():
    class Customer:
        name, phone, email = "Ana de Souza", PHONE, EMAIL

    values = known_values(Customer())

    assert {"Ana de Souza", "Ana", "Souza", PHONE, EMAIL} <= set(values)
    assert "de" not in values


def test_save_creates_then_updates(conn):
    user = user_id_for(conn, 1)
    stored_id = save(conn, None, user, messages(), KNOWN, NOW)

    assert save(conn, stored_id, user, messages("Depois"), KNOWN, NOW + timedelta(minutes=1)) == stored_id
    rows = conn.execute("SELECT * FROM stored_conversations").fetchall()
    assert len(rows) == 1
    assert "Depois" in rows[0]["messages"]
    assert rows[0]["user_id"] == user


def test_only_one_conversation_stays_open_and_the_most_recent_wins(conn):
    user = user_id_for(conn, 1)
    first = save(conn, None, user, messages("primeira"), KNOWN, NOW)
    second = save(conn, None, user, messages("segunda"), KNOWN, NOW + timedelta(minutes=1))

    assert conn.execute("SELECT status FROM stored_conversations WHERE stored_id = ?", (first,)).fetchone()[0] == "closed"
    assert find_open(conn, user, NOW + timedelta(minutes=2))[0] == second


def test_find_open_returns_a_masked_transcript(conn):
    user = user_id_for(conn, 1)
    stored_id = save(conn, None, user, messages(), KNOWN, NOW)

    found_id, transcript = find_open(conn, user, NOW + timedelta(minutes=5))

    assert found_id == stored_id
    assert "Cliente:" in transcript
    assert "Assistente:" in transcript
    assert "ana.souza" not in transcript
    assert "pensando" not in transcript


def test_find_open_skips_the_conversation_in_progress(conn):
    user = user_id_for(conn, 1)
    stored_id = save(conn, None, user, messages(), KNOWN, NOW)

    assert find_open(conn, user, NOW, exclude=stored_id) is None


def test_another_customers_conversation_is_never_found(conn):
    save(conn, None, user_id_for(conn, 1), messages(), KNOWN, NOW)

    assert find_open(conn, user_id_for(conn, 2), NOW) is None


def test_thirty_minutes_without_a_message_closes_it(conn):
    user = user_id_for(conn, 1)
    stored_id = save(conn, None, user, messages(), KNOWN, NOW)

    assert find_open(conn, user, NOW + timedelta(minutes=29))[0] == stored_id
    assert find_open(conn, user, NOW + timedelta(minutes=30)) is None
    assert conn.execute("SELECT status FROM stored_conversations").fetchone()[0] == "closed"


def test_time_limit_holds_in_the_stores_timezone(conn):
    local = NOW.astimezone(ZoneInfo("America/Campo_Grande"))
    user = user_id_for(conn, 1)
    save(conn, None, user, messages(), KNOWN, local)

    assert find_open(conn, user, local + timedelta(minutes=29)) is not None
    assert find_open(conn, user, local + timedelta(minutes=30)) is None


def test_closed_conversation_stays_stored_and_cannot_continue(conn):
    user = user_id_for(conn, 1)
    stored_id = save(conn, None, user, messages(), KNOWN, NOW)

    close(conn, stored_id)

    assert find_open(conn, user, NOW) is None
    assert conn.execute("SELECT count(*) FROM stored_conversations").fetchone()[0] == 1


# Through the agent, with the store's real tools and a scripted model.


def owner(conn, order_id):
    return conn.execute(
        "SELECT c.phone, c.email, c.name FROM orders o JOIN customers c USING (customer_id) WHERE o.order_id = ?",
        (order_id,),
    ).fetchone()


def scripted(call_order=None):
    """Calls the order tool when a message starts with 'pedido', then repeats any previous conversation."""

    def function(messages, _info):
        last_request = messages[-1].parts
        text = next((p.content for p in last_request if isinstance(p, UserPromptPart)), "")
        returned = [p for p in last_request if isinstance(p, ToolReturnPart)]
        if text.startswith("pedido"):
            _, code, phone, email = text.split("|")
            return ModelResponse(parts=[ToolCallPart("get_order_status", {"tracking_code": code, "phone": phone, "email": email})])
        if returned and returned[0].tool_name == "get_order_status":
            previous = returned[0].content.get("previous_conversation", {})
            return ModelResponse(parts=[TextPart(str(previous.get("transcript", "nada")))])
        return ModelResponse(parts=[TextPart(f"eco {text}")])

    return FunctionModel(function)


@pytest.fixture
def agent(store_db):
    tools = [Tool(_get_order_status, name="get_order_status"), Tool(_find_open_conversation, name="find_open_conversation")]
    return StoreAgent(scripted(), primary_model="function", settings={}, reply_timeout_seconds=30, tools=tools, db_path=store_db)


def order_message(conn, order_id):
    customer = owner(conn, order_id)
    code = conn.execute("SELECT tracking_code FROM orders WHERE order_id = ?", (order_id,)).fetchone()[0]
    return f"pedido|{code}|{customer['phone']}|{customer['email']}"


def stored(conn):
    return conn.execute("SELECT * FROM stored_conversations ORDER BY rowid").fetchall()


def test_nothing_is_stored_before_identification(agent, conn):
    agent.respond("c1", "oi")

    assert stored(conn) == []


def test_identification_stores_the_earlier_messages_masked(agent, conn):
    customer = owner(conn, 1)
    agent.respond("c1", f"oi, meu telefone é {customer['phone']}")
    agent.respond("c1", order_message(conn, 1))

    rows = stored(conn)
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    assert "oi, meu telefone" in rows[0]["messages"]
    for private in (customer["phone"], customer["email"], customer["name"]):
        assert private not in rows[0]["messages"]


def test_a_reload_continues_the_open_conversation_after_verifying_again(agent, conn):
    agent.respond("before-reload", order_message(conn, 1))
    agent.respond("before-reload", "algo importante")

    reply = agent.respond("after-reload", order_message(conn, 1))

    assert "algo importante" in reply.answer
    assert len(stored(conn)) == 1


def test_the_tool_finds_nothing_more_once_the_order_check_found_it(agent, conn, store_db):
    agent.respond("before-reload", order_message(conn, 1))
    agent.respond("after-reload", order_message(conn, 1))
    session = agent._sessions.get("after-reload")

    assert find_open(conn, session.user_id, datetime.now(UTC), exclude=session.stored_id) is None


def test_a_new_session_without_verifying_continues_nothing(agent, conn):
    agent.respond("before-reload", order_message(conn, 1))
    agent.respond("before-reload", "algo importante")

    assert "algo importante" not in agent.respond("after-reload", "oi").answer


def test_end_conversation_closes_the_stored_conversation(agent, conn):
    agent.respond("c1", order_message(conn, 1))
    agent.respond("c1", "algo importante")

    agent.end_conversation("c1")

    assert stored(conn)[0]["status"] == "closed"
    assert "algo importante" not in agent.respond("c2", order_message(conn, 1)).answer


def test_a_second_customer_closes_the_first_and_clears_the_history(agent, conn):
    agent.respond("c1", order_message(conn, 1))
    other = other_customers_order(conn)

    agent.respond("c1", order_message(conn, other))
    agent.respond("c1", "depois")

    rows = stored(conn)
    assert [row["status"] for row in rows] == ["closed", "open"]
    assert rows[0]["user_id"] != rows[1]["user_id"]
    assert owner(conn, 1)["email"].split("@")[0] not in rows[1]["messages"]
    assert "pedido|BRAB1234567BR|" not in rows[1]["messages"]


def watching_agent(store_db, seen, fail=()):
    """Records each request the model receives, and fails on the order check's result while `fail` holds anything."""
    script = scripted().function

    def function(messages, info):
        seen.append((repr(messages), info.instructions))
        if fail and isinstance(messages[-1].parts[0], ToolReturnPart):
            raise ModelAPIError("primary", "server down")
        return script(messages, info)

    tools = [Tool(_get_order_status, name="get_order_status")]
    return StoreAgent(FunctionModel(function), primary_model="function", settings={}, reply_timeout_seconds=30, tools=tools, db_path=store_db)


def other_customers_order(conn):
    return conn.execute("SELECT min(order_id) FROM orders WHERE tracking_code IS NOT NULL AND customer_id <> (SELECT customer_id FROM orders WHERE order_id = 1)").fetchone()[0]


def test_requests_after_a_second_customer_verifies_have_no_trace_of_the_first(store_db, conn):
    seen = []
    agent = watching_agent(store_db, seen)
    agent.respond("c1", order_message(conn, 1))
    first_email = owner(conn, 1)["email"]
    seen.clear()

    agent.respond("c1", order_message(conn, other_customers_order(conn)))
    agent.respond("c1", "depois")

    requests = [request for request, _ in seen]
    assert first_email in requests[0], "the switch isn't known until the order check returns"
    assert len(requests) == 3
    assert all(first_email not in request for request in requests[1:])
    assert "get_order_status" in requests[1]
    assert all("Empório" in instructions for _, instructions in seen)


def test_a_failed_reply_after_the_switch_does_not_bring_the_first_customer_back(store_db, conn):
    seen, fail = [], []
    agent = watching_agent(store_db, seen, fail)
    agent.respond("c1", order_message(conn, 1))
    first_email = owner(conn, 1)["email"]
    fail.append(True)
    with pytest.raises(ProviderError):
        agent.respond("c1", order_message(conn, other_customers_order(conn)))
    fail.clear()
    seen.clear()

    agent.respond("c1", "depois")

    assert first_email not in seen[0][0]


def test_the_same_customer_verifying_again_keeps_the_history(store_db, conn):
    seen = []
    agent = watching_agent(store_db, seen)
    agent.respond("c1", order_message(conn, 1))
    agent.respond("c1", "algo importante")

    agent.respond("c1", order_message(conn, 1))

    assert "algo importante" in seen[-1][0]


def test_failed_verification_identifies_nobody(agent, conn):
    agent.respond("c1", "pedido|BRAB1234567BR|(67) 90000-0000|wrong@example.com")

    assert stored(conn) == []


def test_session_store_expiry_uses_the_same_limit():
    moment = [NOW]
    sessions = SessionStore(clock=lambda: moment[0])
    first = sessions.get("c1")

    moment[0] += timedelta(minutes=30)

    assert sessions.get("c1") is not first
