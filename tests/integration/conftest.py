from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).parents[2] / "src" / "emporio" / "chat" / "app.py")
RUN_TIMEOUT_SECONDS = 15


@pytest.fixture(autouse=True)
def startup_settings(monkeypatch):
    monkeypatch.setenv("EMPORIO_AGENT", "stand_in")
    monkeypatch.setenv("EMPORIO_TROUBLESHOOTING", "0")
    monkeypatch.setenv("EMPORIO_REPLY_TIMEOUT_SECONDS", "5")
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def open_app():
    def _open_app():
        return AppTest.from_file(APP_PATH, default_timeout=RUN_TIMEOUT_SECONDS).run()

    return _open_app


def send(app, message):
    return app.chat_input[0].set_value(message).run()


def page_text(app):
    elements = [
        *app.text,
        *app.markdown,
        *app.caption,
        *app.error,
        *app.warning,
        *app.info,
        *app.code,
        *app.json,
        *app.title,
    ]
    return "\n".join(str(element.value) for element in elements)
