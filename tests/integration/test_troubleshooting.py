import pytest
from conftest import page_text, send

from emporio.agent.contract import AgentReply, ReplyDetails, Step
from emporio.agent.factory import AGENTS
from emporio.agent.stand_in import FAKE_API_KEY


@pytest.fixture(autouse=True)
def troubleshooting_on(monkeypatch):
    monkeypatch.setenv("EMPORIO_TROUBLESHOOTING", "1")


class FixedAgent:
    name = "fixed"
    is_simulated = True

    def __init__(self, reply):
        self.reply = reply

    def respond(self, conversation_id, message):
        return self.reply


@pytest.fixture
def use_reply(monkeypatch):
    def _use_reply(reply):
        monkeypatch.setitem(AGENTS, "fixed", lambda _settings: FixedAgent(reply))
        monkeypatch.setenv("EMPORIO_AGENT", "fixed")

    return _use_reply


def shown_label(expander):
    """The label as a person reads it, without the Markdown escapes."""
    return expander.label.replace("\\", "")


def test_tool_reply_shows_steps_sources_model_provider_and_time(open_app):
    app = send(open_app(), "/ferramenta")
    text = page_text(app)

    assert app.expander[0].label == "Reply details"
    assert app.expander[0].proto.expanded is False
    assert "buscar_produto" in shown_label(app.expander[1])
    assert "tool" in shown_label(app.expander[1])
    assert "120 ms" in shown_label(app.expander[1])
    assert "violão" in text
    assert "Violão simulado" in text
    assert "data: products" in text
    assert "Model: stand-in" in text
    assert "Provider: simulated" in text
    assert "Fallback used: no" in text
    assert "Total time:" in text
    assert "Details: complete" in text


def test_policy_reply_shows_a_policy_source(open_app):
    assert "policy: Seção simulada" in page_text(send(open_app(), "/politica"))


def test_fallback_is_shown(open_app):
    assert "Fallback used: yes" in page_text(send(open_app(), "/fallback"))


def test_reasoning_is_shown_as_a_step(open_app):
    app = send(open_app(), "/raciocinio")

    assert "reasoning" in app.expander[1].label
    assert "respondo diretamente" in page_text(app)


def test_reply_without_tools_or_sources_says_so(open_app):
    text = page_text(send(open_app(), "Olá"))

    assert "No tools or other steps were used." in text
    assert "No sources were used." in text


def test_missing_details_are_marked_unavailable(open_app):
    app = send(open_app(), "/sem-detalhes")
    text = page_text(app)

    assert "Details: unavailable" in text
    assert "No tools or other steps were used." not in text
    assert "resposta simulada" in text


def test_partial_details_are_marked_incomplete(open_app):
    assert "Details: incomplete" in page_text(send(open_app(), "/incompleto"))


def test_failure_has_details_and_the_customer_text_stays_friendly(open_app):
    app = send(open_app(), "/erro")

    assert "Falha simulada" in page_text(app)
    assert "Falha simulada" not in app.chat_message[1].text[0].value
    assert "(67) 3341-4444" in app.chat_message[1].text[0].value


def test_timeout_has_details(open_app, monkeypatch):
    monkeypatch.setenv("EMPORIO_REPLY_TIMEOUT_SECONDS", "0.1")

    assert "timed out" in page_text(send(open_app(), "/lento"))


def test_failed_step_is_identified(open_app):
    app = send(open_app(), "/sensivel")

    assert "chamar_servico" in shown_label(app.expander[1])
    assert "error" in shown_label(app.expander[1])


def test_fake_key_is_never_shown(open_app):
    app = send(open_app(), "/sensivel")

    assert FAKE_API_KEY not in page_text(app)
    assert FAKE_API_KEY not in str(app.session_state["conversation"])
    assert "[REMOVIDO]" in page_text(app)


def test_every_reply_has_its_own_details(open_app):
    app = open_app()
    for message in ("Olá", "/erro", "/sem-detalhes", "/ferramenta"):
        send(app, message)

    assert [e.label for e in app.expander].count("Reply details") == 4


def test_large_details_show_a_summary_and_open_a_modal(open_app):
    app = send(open_app(), "/grande")

    assert [e.label for e in app.expander] == ["Reply details"]
    assert "etapa_1" not in page_text(app)

    app.button(key="open_details_0").click().run()

    assert sum("etapa_" in shown_label(expander) for expander in app.expander) == 12
    assert ("Resultado simulado. " * 150).strip() in page_text(app)


def test_long_value_is_shortened_inline_and_complete_in_the_modal(open_app, use_reply):
    long_value = "x" * 2500
    use_reply(AgentReply("Resposta", ReplyDetails(steps=(Step(name="passo", kind="tool", result=long_value),))))

    app = send(open_app(), "Olá")

    assert long_value not in page_text(app)
    assert "shortened" in page_text(app)

    app.button(key="open_details_0").click().run()

    assert long_value in page_text(app)


@pytest.mark.parametrize(
    ("steps", "opens_modal"),
    [(10, False), (11, True)],
)
def test_step_limit_for_the_modal(open_app, use_reply, steps, opens_modal):
    use_reply(
        AgentReply(
            "Resposta",
            ReplyDetails(steps=tuple(Step(name=f"passo_{n}", kind="tool") for n in range(steps))),
        )
    )

    app = send(open_app(), "Olá")

    assert any(button.key == "open_details_0" for button in app.button) is opens_modal


def test_character_limit_for_the_modal(open_app, use_reply):
    steps = tuple(Step(name=f"passo_{n}", kind="tool", result="x" * 1900) for n in range(4))
    use_reply(AgentReply("Resposta", ReplyDetails(steps=steps)))

    app = send(open_app(), "Olá")

    assert any(button.key == "open_details_0" for button in app.button)
    assert [e.label for e in app.expander] == ["Reply details"]


def test_step_names_cannot_add_formatting_to_labels(open_app, use_reply):
    use_reply(AgentReply("Resposta", ReplyDetails(steps=(Step(name="**x** [y](z)", kind="tool"),))))

    app = send(open_app(), "Olá")

    assert "**x**" not in app.expander[1].label
    assert "\\*\\*x\\*\\*" in app.expander[1].label


def test_troubleshooting_off_shows_nothing_and_has_no_control(open_app, monkeypatch):
    monkeypatch.setenv("EMPORIO_TROUBLESHOOTING", "0")

    app = send(open_app(), "/ferramenta")

    assert len(app.expander) == 0
    assert "buscar_produto" not in page_text(app)
    assert len(app.toggle) == 0
    assert len(app.checkbox) == 0
    assert not any(button.key.startswith("open_details") for button in app.button)
