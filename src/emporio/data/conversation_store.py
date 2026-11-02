import asyncio
import re
import sqlite3
import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelResponse,
    TextPart,
    ThinkingPart,
    UserPromptPart,
)

SESSION_LIMIT = timedelta(minutes=30)
MIN_NAME_PART_LENGTH = 3
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w.-])(?:\+?55[\s-]*)?\(?\d{2}\)?[\s-]*9?\d{4}[\s-]?\d{4}(?!\w)")


def mask(text: str, known_values: Sequence[str] = ()) -> str:
    text = PHONE.sub("[telefone]", EMAIL.sub("[email]", text))
    for value in sorted(filter(None, known_values), key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(value)}(?!\w)", "[nome]", text)
    return text


def known_values(customer: Any) -> tuple[str, ...]:
    """Name parts too, because a reply greets the customer by first name."""
    parts = [part for part in customer.name.split() if len(part) >= MIN_NAME_PART_LENGTH]
    return (customer.name, *parts, customer.phone, customer.email)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Session:
    last_message_at: datetime
    history: list[ModelMessage] = field(default_factory=list)
    closed: bool = False
    customer: Any = None
    user_id: str | None = None
    stored_id: str | None = None
    history_reset: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def is_over(self, now: datetime) -> bool:
        return self.closed or now - self.last_message_at >= SESSION_LIMIT


class SessionStore:
    def __init__(self, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, conversation_id: str) -> Session:
        """A session that ended is replaced here, so the next message starts fresh under the same ID."""
        now = self._clock()
        with self._lock:
            current = self._sessions.get(conversation_id)
            self._sessions = {key: value for key, value in self._sessions.items() if not value.is_over(now)}
            if current is None or current.is_over(now):
                current = Session(last_message_at=now)
            self._sessions[conversation_id] = current
            return current

    def touch(self, session: Session) -> None:
        session.last_message_at = self._clock()

    def end(self, conversation_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(conversation_id)
            if session is not None:
                session.closed = True
            return session


def user_id_for(conn: sqlite3.Connection, customer_id: int) -> str:
    row = conn.execute("SELECT user_id FROM customer_identities WHERE customer_id = ?", (customer_id,)).fetchone()
    if row:
        return row[0]
    user_id = uuid.uuid4().hex
    conn.execute("INSERT INTO customer_identities VALUES (?, ?)", (user_id, customer_id))
    conn.commit()
    return user_id


def serialize(messages: Sequence[ModelMessage], values: Sequence[str]) -> str:
    kept: list[ModelMessage] = []
    for message in messages:
        if isinstance(message, ModelResponse):
            parts = [part for part in message.parts if not isinstance(part, ThinkingPart)]
            if not parts:
                continue
            message = replace(message, parts=parts)
        kept.append(message)
    return mask(ModelMessagesTypeAdapter.dump_json(kept).decode(), values)


def save(
    conn: sqlite3.Connection,
    stored_id: str | None,
    user_id: str,
    messages: Sequence[ModelMessage],
    values: Sequence[str],
    now: datetime,
) -> str:
    stored = serialize(messages, values)
    updated_at = now.astimezone(UTC).isoformat()
    if stored_id is not None:
        conn.execute(
            "UPDATE stored_conversations SET messages = ?, updated_at = ? WHERE stored_id = ?",
            (stored, updated_at, stored_id),
        )
        conn.commit()
        return stored_id
    conn.execute("UPDATE stored_conversations SET status = 'closed' WHERE user_id = ? AND status = 'open'", (user_id,))
    stored_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO stored_conversations VALUES (?, ?, 'open', ?, ?)",
        (stored_id, user_id, stored, updated_at),
    )
    conn.commit()
    return stored_id


def close(conn: sqlite3.Connection, stored_id: str) -> None:
    conn.execute("UPDATE stored_conversations SET status = 'closed' WHERE stored_id = ?", (stored_id,))
    conn.commit()


def _transcript(stored: str) -> str:
    lines = []
    for message in ModelMessagesTypeAdapter.validate_json(stored):
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                lines.append(f"Cliente: {part.content}")
            elif isinstance(part, TextPart):
                lines.append(f"Assistente: {part.content}")
    return "\n".join(lines)


def find_open(
    conn: sqlite3.Connection,
    user_id: str,
    now: datetime,
    exclude: str | None = None,
) -> tuple[str, str] | None:
    limit = (now - SESSION_LIMIT).astimezone(UTC).isoformat()
    conn.execute(
        "UPDATE stored_conversations SET status = 'closed' WHERE user_id = ? AND status = 'open' AND updated_at <= ?",
        (user_id, limit),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT stored_id, messages FROM stored_conversations
        WHERE user_id = ? AND status = 'open' AND stored_id IS NOT ?
        ORDER BY updated_at DESC LIMIT 1
        """,
        (user_id, exclude),
    ).fetchone()
    return (row[0], _transcript(row[1])) if row else None
