import asyncio
import re
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from pydantic_ai.messages import ModelMessage

SESSION_LIMIT = timedelta(minutes=30)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w.-])(?:\+?55[\s-]*)?\(?\d{2}\)?[\s-]*9?\d{4}[\s-]?\d{4}(?!\w)")


def mask(text: str, known_values: Sequence[str] = ()) -> str:
    """Exact known values go first, because the patterns can't recognize a name."""
    for value in known_values:
        if value:
            text = text.replace(value, "[nome]")
    return PHONE.sub("[telefone]", EMAIL.sub("[email]", text))


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Session:
    last_message_at: datetime
    history: list[ModelMessage] = field(default_factory=list)
    closed: bool = False
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

    def end(self, conversation_id: str) -> None:
        with self._lock:
            session = self._sessions.get(conversation_id)
            if session is not None:
                session.closed = True
