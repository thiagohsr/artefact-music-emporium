from typing import ClassVar

import pytest
from conftest import APP_PATH, RUN_TIMEOUT_SECONDS, send
from streamlit.testing.v1 import AppTest

from emporio.agent.contract import AgentReply
from emporio.agent.factory import AGENTS


class CountingAgent:
    name = "counting"
    is_simulated = True
    calls: ClassVar[list] = []

    def respond(self, conversation_id, message):
        self.calls.append((conversation_id, message))
        return AgentReply(f"Resposta para {message}")

    def end_conversation(self, conversation_id):
        pass


@pytest.fixture(autouse=True)
def counting_agent(monkeypatch):
    CountingAgent.calls = []
    monkeypatch.setitem(AGENTS, "counting", lambda _settings: CountingAgent())
    monkeypatch.setenv("EMPORIO_AGENT", "counting")


def reload_page(link):
    app = AppTest.from_file(APP_PATH, default_timeout=RUN_TIMEOUT_SECONDS)
    if link is not None:
        app.query_params["conversa"] = link
    return app.run()


def messages(app):
    return [(message.text if message.name == "user" else message.markdown)[0].value for message in app.chat_message]


def test_a_reload_with_the_link_brings_the_conversation_back(open_app):
    app = send(open_app(), "Olá")
    link = app.query_params["conversa"]

    reloaded = reload_page(link)

    assert messages(reloaded) == ["Olá", "Resposta para Olá"]
    assert not reloaded.exception


def test_a_message_after_the_reload_continues_with_the_same_agent_conversation(open_app):
    app = send(open_app(), "Olá")

    send(reload_page(app.query_params["conversa"]), "De novo")

    assert [conversation_id for conversation_id, _ in CountingAgent.calls] == [app.session_state["conversation"].id] * 2


def test_an_unknown_link_starts_a_new_conversation_under_a_new_identifier():
    app = reload_page("inventado")

    assert messages(app) == []
    assert app.query_params["conversa"] != "inventado"


def test_a_new_conversation_changes_the_link_and_the_old_one_stops_working(open_app):
    app = send(open_app(), "Olá")
    old_link = app.query_params["conversa"]

    app.button(key="new_conversation").click().run()
    app.button(key="confirm_new_conversation").click().run()

    assert app.query_params["conversa"] != old_link
    assert messages(reload_page(old_link)) == []
