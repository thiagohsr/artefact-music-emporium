from typing import Any

from emporio.data.conversation_store import Session


def finish_conversation(session: Session) -> dict[str, Any]:
    session.closed = True
    return {"closed": True}
