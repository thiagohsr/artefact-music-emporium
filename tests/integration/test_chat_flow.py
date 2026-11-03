import pytest
from conftest import page_text, send

from emporio.agent.contract import AgentReply
from emporio.agent.factory import AGENTS
from emporio.chat.conversation import MAX_MESSAGE_LENGTH

WHATSAPP_NUMBERS = ("(67) 3341-4444", "(67) 3321-4500")
EMAIL = "contato@emporiodamusica.com.br"


class RecordingAgent:
    name = "recording"
    is_simulated = True
    calls = []

    def respond(self, conversation_id, message):
        self.calls.append((conversation_id, message))
        return AgentReply(f"Resposta para {message}")

    def end_conversation(self, conversation_id):
        pass


@pytest.fixture
def recording_agent(monkeypatch):
    RecordingAgent.calls = []
    monkeypatch.setitem(AGENTS, "recording", lambda _settings: RecordingAgent())
    monkeypatch.setenv("EMPORIO_AGENT", "recording")
    return RecordingAgent


def assert_friendly_failure(app):
    text = page_text(app)
    for contact in (*WHATSAPP_NUMBERS, EMAIL):
        assert contact in text
    assert "Falha simulada" not in text
    assert "RuntimeError" not in text
    assert not app.exception


def test_page_is_in_portuguese_with_an_empty_conversation(open_app):
    app = open_app()

    assert not app.exception
    assert app.chat_message == [] or len(app.chat_message) == 0
    assert app.chat_input[0].disabled is False
    assert "Digite" in app.chat_input[0].placeholder


def test_replies_keep_dollar_signs_out_of_math_and_customer_text_stays_plain(open_app, recording_agent):
    app = send(open_app(), "R$100 e **R$200**")

    assert app.chat_message[0].text[0].value == "R$100 e **R$200**"
    assert app.chat_message[1].markdown[0].value == r"Resposta para R\$100 e **R\$200**"


def test_twenty_message_conversation_stays_in_order_with_one_identifier(open_app, recording_agent):
    app = open_app()

    for number in range(20):
        send(app, f"Mensagem {number}")

    expected = []
    for number in range(20):
        expected += [f"Mensagem {number}", f"Resposta para Mensagem {number}"]
    shown = [(message.text if message.name == "user" else message.markdown)[0].value for message in app.chat_message]
    assert shown == expected
    assert len({conversation_id for conversation_id, _ in recording_agent.calls}) == 1
    assert app.chat_input[0].disabled is False


def test_new_conversation_clears_messages_and_changes_the_identifier(open_app, recording_agent):
    app = open_app()
    send(app, "Primeira")

    app.button(key="new_conversation").click().run()
    app.button(key="confirm_new_conversation").click().run()

    assert len(app.text) == 0
    send(app, "Segunda")
    first_id, second_id = (conversation_id for conversation_id, _ in recording_agent.calls)
    assert first_id != second_id


def test_markup_is_shown_literally(open_app):
    message = "**negrito** <b>teste</b> [link](http://exemplo.com)"

    app = send(open_app(), message)

    assert app.text[0].value == message
    assert message not in "\n".join(element.value for element in app.markdown)


def test_blank_messages_are_not_sent(open_app, recording_agent):
    app = send(open_app(), "   ")

    assert recording_agent.calls == []
    assert len(app.text) == 0


def test_over_limit_message_opens_the_edit_panel_with_the_full_text(open_app, recording_agent):
    long_text = "a" * (MAX_MESSAGE_LENGTH + 1)

    app = send(open_app(), long_text)

    assert recording_agent.calls == []
    assert str(MAX_MESSAGE_LENGTH + 1) in app.error[0].value
    assert "2.000" in app.error[0].value
    assert app.text_area[0].value == long_text


def test_still_long_edit_is_rejected_again(open_app, recording_agent):
    app = send(open_app(), "a" * (MAX_MESSAGE_LENGTH + 1))

    longer_text = "b" * (MAX_MESSAGE_LENGTH + 5)
    app.text_area[0].set_value(longer_text)
    app.button(key="send_draft").click().run()

    assert recording_agent.calls == []
    assert str(MAX_MESSAGE_LENGTH + 5) in app.error[0].value
    assert app.text_area[0].value == longer_text


def test_shortened_edit_is_sent(open_app, recording_agent):
    app = send(open_app(), "a" * (MAX_MESSAGE_LENGTH + 1))

    app.text_area[0].set_value("Mensagem curta")
    app.button(key="send_draft").click().run()

    assert [message for _, message in recording_agent.calls] == ["Mensagem curta"]
    assert len(app.error) == 0
    assert len(app.text_area) == 0


def test_blank_edit_closes_the_panel(open_app, recording_agent):
    app = send(open_app(), "a" * (MAX_MESSAGE_LENGTH + 1))

    app.text_area[0].set_value("   ")
    app.button(key="send_draft").click().run()

    assert recording_agent.calls == []
    assert len(app.error) == 0
    assert len(app.text_area) == 0


def test_discard_closes_the_panel(open_app, recording_agent):
    app = send(open_app(), "a" * (MAX_MESSAGE_LENGTH + 1))

    app.button(key="discard_draft").click().run()

    assert recording_agent.calls == []
    assert len(app.error) == 0
    assert len(app.text_area) == 0


def test_new_message_while_the_panel_is_open_closes_it(open_app, recording_agent):
    app = send(open_app(), "a" * (MAX_MESSAGE_LENGTH + 1))

    send(app, "Outra mensagem")

    assert [message for _, message in recording_agent.calls] == ["Outra mensagem"]
    assert len(app.text_area) == 0


def test_agent_error_shows_the_friendly_message_and_the_chat_still_works(open_app):
    app = send(open_app(), "/erro")

    assert_friendly_failure(app)

    send(app, "Olá")

    assert len(app.chat_message) == 4
    assert app.chat_input[0].disabled is False


def test_timeout_shows_the_friendly_message(open_app, monkeypatch):
    monkeypatch.setenv("EMPORIO_REPLY_TIMEOUT_SECONDS", "0.1")

    app = send(open_app(), "/lento")

    assert_friendly_failure(app)
    assert app.chat_input[0].disabled is False


def test_two_sessions_do_not_share_messages(open_app):
    first = send(open_app(), "Mensagem da primeira sessão")
    second = send(open_app(), "Mensagem da segunda sessão")

    assert "segunda" not in page_text(first)
    assert "primeira" not in page_text(second)
    assert first.session_state["conversation"].id != second.session_state["conversation"].id


@pytest.mark.parametrize("message", ["/ferramenta", "/erro", "/sensivel", "/grande"])
def test_no_internal_details_with_troubleshooting_off(open_app, message):
    app = send(open_app(), message)

    assert len(app.expander) == 0
    assert app.session_state["conversation"].turns[0].details is None
    text = page_text(app)
    for internal in ("buscar_produto", "chamar_servico", "stand-in", "etapa_1", "Falha simulada"):
        assert internal not in text
