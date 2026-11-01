import pytest
from conftest import page_text, send


def test_notice_shows_replies_are_simulated(open_app):
    app = open_app()

    assert any("simuladas" in notice.value for notice in app.info)


def test_notice_stays_during_a_conversation(open_app):
    app = send(open_app(), "Olá")

    assert any("simuladas" in notice.value for notice in app.info)


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("EMPORIO_AGENT", "planted-unknown-agent"),
        ("EMPORIO_TROUBLESHOOTING", "planted-flag"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "planted-seconds"),
    ],
)
def test_invalid_setting_shows_an_error_page_without_a_chat(open_app, monkeypatch, setting, value):
    monkeypatch.setenv(setting, value)

    app = open_app()

    assert not app.exception
    assert setting in app.error[0].value
    assert value not in page_text(app)
    assert len(app.chat_input) == 0
    assert len(app.info) == 0


def test_error_page_recovers_after_the_setting_is_fixed(open_app, monkeypatch):
    monkeypatch.setenv("EMPORIO_AGENT", "planted-unknown-agent")
    assert len(open_app().chat_input) == 0

    monkeypatch.setenv("EMPORIO_AGENT", "stand_in")

    assert len(open_app().chat_input) == 1
