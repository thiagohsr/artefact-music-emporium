import sqlite3
from datetime import datetime
from typing import Any

from emporio.data.conversation_store import Session, find_open


def finish_conversation(session: Session) -> dict[str, Any]:
    session.closed = True
    return {"closed": True}


def find_open_conversation(conn: sqlite3.Connection, session: Session, now: datetime) -> dict[str, Any]:
    if session.user_id is None:
        return {"found": False}
    found = find_open(conn, session.user_id, now, exclude=session.stored_id)
    if found is None:
        return {"found": False}
    session.stored_id, transcript = found
    return {"found": True, "transcript": transcript}
