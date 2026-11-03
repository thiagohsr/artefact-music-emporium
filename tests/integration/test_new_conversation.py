import pytest
from conftest import send

from emporio.agent.contract import AgentReply
from emporio.agent.factory import AGENTS


class EndingAgent:
    name = "ending"
    is_simulated = True
    ended = []

    def respond(self, conversation_id, message):
        return AgentReply(f"Resposta para {message}")

    def end_conversation(self, conversation_id):
        self.ended.append(conversation_id)


@pytest.fixture(autouse=True)
def ending_agent(monkeypatch):
    EndingAgent.ended = []
    monkeypatch.setitem(AGENTS, "ending", lambda _settings: EndingAgent())
    monkeypatch.setenv("EMPORIO_AGENT", "ending")


def open_modal(app):
    return app.button(key="new_conversation").click().run()


def has_modal(app):
    return any(button.key == "confirm_new_conversation" for button in app.button)


def test_the_button_opens_a_modal_in_portuguese_and_changes_nothing_yet(open_app):
    app = send(open_app(), "Olá")
    identifier = app.session_state["conversation"].id

    open_modal(app)

    assert has_modal(app)
    assert any("Cancelar" in button.label for button in app.button)
    assert any("Confirmar" in button.label for button in app.button)
    assert app.session_state["conversation"].id == identifier
    assert app.text[0].value == "Olá"
    assert EndingAgent.ended == []


def test_cancel_changes_nothing(open_app):
    app = open_modal(send(open_app(), "Olá"))
    identifier = app.session_state["conversation"].id

    app.button(key="cancel_new_conversation").click().run()

    assert not has_modal(app)
    assert app.session_state["conversation"].id == identifier
    assert app.text[0].value == "Olá"
    assert EndingAgent.ended == []


def test_confirm_ends_the_conversation_and_clears_the_page(open_app):
    app = open_modal(send(open_app(), "Olá"))
    identifier = app.session_state["conversation"].id

    app.button(key="confirm_new_conversation").click().run()

    assert not has_modal(app)
    assert EndingAgent.ended == [identifier]
    assert app.session_state["conversation"].id != identifier
    assert len(app.chat_message) == 0
