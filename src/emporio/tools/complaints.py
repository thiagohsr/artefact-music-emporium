import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from emporio.data.conversation_store import mask

RETURN_TIME = "24 horas úteis"


def register_complaint(
    conn: sqlite3.Connection,
    summary: str,
    user_id: str | None = None,
    known_values: Sequence[str] = (),
) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO complaints (user_id, summary, created_at) VALUES (?, ?, ?)",
        (user_id, mask(summary, known_values), datetime.now(UTC).isoformat()),
    )
    conn.commit()
    return {"recorded": True, "return_time": RETURN_TIME}
