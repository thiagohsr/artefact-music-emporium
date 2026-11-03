import contextlib
import sqlite3

from seed_db import CSV_DIR, seed


def tables(path):
    with contextlib.closing(sqlite3.connect(path)) as conn:
        return {name for name, in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_seed_creates_the_agent_tables(store_db):
    assert {"customer_identities", "stored_conversations", "complaints"} <= tables(store_db)


def test_reseeding_keeps_agent_rows_and_reloads_store_tables(store_db):
    with contextlib.closing(sqlite3.connect(store_db)) as conn, conn:
        conn.execute("INSERT INTO customer_identities VALUES ('user-1', 1)")
        conn.execute("INSERT INTO stored_conversations VALUES ('s1', 'user-1', 'open', '[]', '2026-01-01T00:00:00+00:00')")
        conn.execute("INSERT INTO complaints (user_id, summary, created_at) VALUES ('user-1', 'x', '2026-01-01T00:00:00+00:00')")
        conn.execute("DELETE FROM order_items WHERE order_id = 1")

    counts = seed(store_db, CSV_DIR)

    assert counts["order_items"] == 22
    with contextlib.closing(sqlite3.connect(store_db)) as conn:
        assert conn.execute("SELECT count(*) FROM stored_conversations").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM complaints").fetchone() == (1,)
        assert conn.execute("SELECT customer_id FROM customer_identities").fetchone() == (1,)
