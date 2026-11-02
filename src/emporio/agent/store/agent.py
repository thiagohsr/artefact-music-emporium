import asyncio
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RunContext, Tool
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError
from pydantic_ai.models import Model

from emporio.agent.contract import AgentReply
from emporio.agent.store.prompt import STORE_ZONE, build_instructions, load_guidance
from emporio.agent.store.providers import build_model
from emporio.agent.store.trace import build_details
from emporio.data.conversation_store import Session, SessionStore
from emporio.data.policy_index import read_settings
from emporio.data.store_db import DB_PATH
from emporio.errors import ProviderError

RUN_LIMIT_MARGIN_SECONDS = 5


def store_now() -> datetime:
    return datetime.now(STORE_ZONE)


@dataclass
class Turn:
    session: Session
    conversation_id: str
    db_path: Path
    settings: Mapping[str, str]
    now: datetime


class StoreAgent:
    name = "store"
    is_simulated = False

    def __init__(
        self,
        model: Model,
        *,
        primary_model: str,
        settings: Mapping[str, str],
        reply_timeout_seconds: float,
        tools: Sequence[Tool] = (),
        db_path: Path = DB_PATH,
        sessions: SessionStore | None = None,
        clock: Callable[[], datetime] = store_now,
    ) -> None:
        self._primary_model = primary_model
        self._settings = settings
        self._db_path = db_path
        self._clock = clock
        self._sessions = sessions or SessionStore()
        # The chat's limit can't stop a running call, so a run stops itself before the chat gives up on it.
        self._run_limit = max(reply_timeout_seconds - RUN_LIMIT_MARGIN_SECONDS, reply_timeout_seconds / 2)
        guidance = load_guidance()
        self._agent = PydanticAgent(model, deps_type=Turn, tools=tools)

        @self._agent.instructions
        def instructions(context: RunContext[Turn]) -> str:
            return build_instructions(guidance, context.deps.now)

        # One loop for the agent's life: the shared HTTP clients break if they cross event loops, and the
        # chat calls from a new thread per reply.
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    def respond(self, conversation_id: str, message: str) -> AgentReply:
        return asyncio.run_coroutine_threadsafe(self._run(conversation_id, message), self._loop).result()

    def end_conversation(self, conversation_id: str) -> None:
        self._sessions.end(conversation_id)

    async def _run(self, conversation_id: str, message: str) -> AgentReply:
        session = self._sessions.get(conversation_id)
        async with session.lock:
            turn = Turn(session, conversation_id, self._db_path, self._settings, self._clock())
            try:
                async with asyncio.timeout(self._run_limit):
                    result = await self._agent.run(message, message_history=session.history, deps=turn)
            except (ModelAPIError, FallbackExceptionGroup) as error:
                raise ProviderError("no model provider answered") from error
            session.history = result.all_messages()
            self._sessions.touch(session)
        return AgentReply(result.output, build_details(result.new_messages(), self._primary_model))


def create_store_agent(reply_timeout_seconds: float) -> StoreAgent:
    settings = read_settings()
    model, primary_model = build_model(settings)
    return StoreAgent(
        model,
        primary_model=primary_model,
        settings=settings,
        reply_timeout_seconds=reply_timeout_seconds,
    )

