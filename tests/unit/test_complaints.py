import sqlite3
from datetime import UTC, datetime

import pytest

from emporio.data.conversation_store import Session, mask
from emporio.tools.complaints import RETURN_TIME, register_complaint
from emporio.tools.conversations import finish_conversation


@pytest.fixture
def conn(store_conn):
    store_conn.row_factory = sqlite3.Row
    return store_conn


def test_complaint_is_stored_and_returns_the_return_time(conn):
    result = register_complaint(conn, "O violão chegou riscado")

    assert result == {"recorded": True, "return_time": RETURN_TIME}
    assert "24 horas úteis" in RETURN_TIME
    row = conn.execute("SELECT summary, user_id, created_at FROM complaints").fetchone()
    assert row["summary"] == "O violão chegou riscado"
    assert row["user_id"] is None
    assert row["created_at"]


def test_complaint_summary_is_masked(conn):
    register_complaint(conn, "Sou Ana Souza, ana@exemplo.com, (67) 99999-1234", known_values=("Ana Souza",))

    summary = conn.execute("SELECT summary FROM complaints").fetchone()["summary"]
    assert "Ana Souza" not in summary
    assert "ana@exemplo.com" not in summary
    assert "99999" not in summary


@pytest.mark.parametrize(
    "text",
    [
        "meu email é a.b+c@exemplo.com.br agora",
        "fone (67) 99123-4567 ok",
        "fone 67 991234567 ok",
        "fone 6733414444 ok",
        "fone +55 67 99123-4567 ok",
    ],
)
def test_mask_removes_emails_and_phones(text):
    masked = mask(text)

    assert "@" not in masked
    assert not any(run in masked for run in ("99123", "991234567", "6733414444"))


@pytest.mark.parametrize("text", ["R$ 2.199,00 em 12x", "pedido 20", "código BRAB1234567BR", "CEP 79202-333", "02/11/2026"])
def test_mask_leaves_ordinary_values(text):
    assert mask(text) == text


def test_mask_is_exact_on_known_values_first():
    assert mask("Ana Souza comprou", ("Ana Souza",)) == "[nome] comprou"


def test_finish_conversation_closes_the_session():
    session = Session(last_message_at=datetime.now(UTC))

    assert finish_conversation(session) == {"closed": True}
    assert session.is_over(session.last_message_at)
