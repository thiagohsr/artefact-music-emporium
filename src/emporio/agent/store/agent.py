import asyncio
import os
import re
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RunContext, Tool
from pydantic_ai.capabilities import Hooks
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError
from pydantic_ai.models import Model, ModelRequestContext

from emporio.agent.contract import AgentReply
from emporio.agent.store.prompt import STORE_ZONE, build_instructions, load_guidance
from emporio.agent.store.providers import build_model
from emporio.agent.store.trace import build_details
from emporio.data.conversation_store import (
    Session,
    SessionStore,
    close,
    known_values,
    save,
    user_id_for,
)
from emporio.data.policy_index import read_settings
from emporio.data.store_db import DB_PATH, read_connection, write_connection
from emporio.errors import ProviderError
from emporio.tools.catalog import get_product, search_products
from emporio.tools.complaints import register_complaint
from emporio.tools.conversations import find_open_conversation, finish_conversation
from emporio.tools.orders import VerifiedCustomer, get_order_status
from emporio.tools.payments import Method, payment_terms
from emporio.tools.policies import policy_lookup

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
    history_length: int = 0
    customer_changed: bool = False


async def _only_current_customer(context: RunContext[Turn], request: ModelRequestContext) -> ModelRequestContext:
    if context.deps.customer_changed:
        request.messages = request.messages[context.deps.history_length :]
    return request


def _search_products(
    context: RunContext[Turn],
    text: str | None = None,
    category: str | None = None,
    min_price_brl: float | None = None,
    max_price_brl: float | None = None,
    in_stock_only: bool = False,
) -> dict[str, Any]:
    with read_connection(context.deps.db_path) as conn:
        return search_products(conn, text, category, min_price_brl, max_price_brl, in_stock_only)


def _get_product(context: RunContext[Turn], name: str) -> dict[str, Any]:
    with read_connection(context.deps.db_path) as conn:
        return get_product(conn, name)


def _payment_terms(
    context: RunContext[Turn],
    installments: int,
    product_name: str | None = None,
    amount_brl: float | None = None,
    method: Method = "credit",
) -> dict[str, Any]:
    with read_connection(context.deps.db_path) as conn:
        return payment_terms(conn, method, product_name, amount_brl, installments)


def _policy_lookup(context: RunContext[Turn], question: str) -> dict[str, Any]:
    return policy_lookup(question, context.deps.settings)


def _get_order_status(context: RunContext[Turn], tracking_code: str, phone: str, email: str) -> dict[str, Any]:
    with read_connection(context.deps.db_path) as conn:
        result, customer = get_order_status(conn, tracking_code, phone, email, context.deps.now.date())
    if customer is None:
        return result
    _identify(context.deps, customer)
    return {
        **result,
        "previous_conversation": _find_open_conversation(context),
        "next_step": "Se o cliente perguntou sobre devolução ou troca, use policy_lookup antes de responder.",
    }


def clean_answer(answer: str) -> str:
    """The self-hosted model sometimes writes a tool call as text after already making it."""
    answer = re.sub(r"<function_call>.*?(</function_call>|$)", "", answer, flags=re.DOTALL)
    lines = [
        line
        for line in answer.splitlines()
        if line.strip(" `*") not in TOOL_NAMES and '"arguments"' not in line and not _BARE_NAME.fullmatch(line.strip())
    ]
    return "\n".join(lines).strip()


def _identify(turn: Turn, customer: VerifiedCustomer) -> None:
    session = turn.session
    with write_connection(turn.db_path) as conn:
        user_id = user_id_for(conn, customer.customer_id)
        if session.user_id not in (None, user_id):
            if session.stored_id:
                close(conn, session.stored_id)
            session.stored_id = None
            # Cleared now, not after the run, so a failed reply can't hand this history to the next turn.
            session.history = []
            turn.customer_changed = True
    session.customer = customer
    session.user_id = user_id


def _find_open_conversation(context: RunContext[Turn]) -> dict[str, Any]:
    with write_connection(context.deps.db_path) as conn:
        return find_open_conversation(conn, context.deps.session, context.deps.now)


def _register_complaint(context: RunContext[Turn], summary: str) -> dict[str, Any]:
    session = context.deps.session
    values = known_values(session.customer) if session.customer else ()
    with write_connection(context.deps.db_path) as conn:
        return register_complaint(conn, summary, session.user_id, values)


def _finish_conversation(context: RunContext[Turn]) -> dict[str, Any]:
    return finish_conversation(context.deps.session)


TOOLS = (
    Tool(
        _search_products,
        name="search_products",
        description=(
            "Use quando o cliente procura opções, ou para achar um produto semelhante em estoque. Filtra por texto, "
            "categoria, faixa de preço e estoque. Categorias: Baixos, Baterias e Percussão, Cordas Orquestrais, "
            "Guitarras, Instrumentos de Sopro (Madeiras), Instrumentos de Sopro (Metais), Teclados e Pianos, "
            "Ukuleles, Violões. Devolve os mais baratos primeiro. Se shown for menor que total, a lista está incompleta: "
            "diga ao cliente quantas opções ficaram de fora e ofereça refinar a busca."
        ),
    ),
    Tool(
        _get_product,
        name="get_product",
        description="Use quando o cliente pergunta sobre um produto específico: preço, estoque, situação, promoção e especificações.",
    ),
    Tool(
        _payment_terms,
        name="payment_terms",
        description=(
            "Use quando o cliente pergunta como pagar, sobre parcelas ou descontos. Informe product_name ou amount_brl, "
            "e installments com o número de parcelas pedido, ou 1 para pagamento à vista. method é credit por padrão, "
            "ou pix, debit ou boleto. Devolve o preço final, o valor da parcela, a parcela mínima e se é permitido."
        ),
    ),
    Tool(
        _policy_lookup,
        name="policy_lookup",
        description="Use quando o cliente pergunta sobre uma regra da loja ou sobre a própria loja: endereço, horários, trocas, frete, garantia, privacidade.",
    ),
    Tool(
        _get_order_status,
        name="get_order_status",
        description=(
            "Use quando o cliente pergunta sobre um pedido. Em tracking_code, informe o código de rastreamento que o cliente "
            "informou: o número do pedido nunca é aceito. Exige também o telefone e o e-mail informados pelo cliente nesta "
            "conversa: nunca invente nem complete esses três dados. Se faltar algum, não chame esta ferramenta e peça o que faltar. Status: pending "
            "(pendente), confirmed (confirmado), shipped (enviado), delivered (entregue), cancelled (cancelado). "
            "estimated_delivery é a previsão de entrega, a única data de entrega conhecida: não há data real de "
            "entrega, então nunca diga em que dia o pedido foi entregue. "
            "days_since_estimate conta os dias desde essa previsão."
        ),
    ),
    Tool(
        _find_open_conversation,
        name="find_open_conversation",
        description=(
            "Devolve a conversa anterior ainda aberta do cliente verificado, se houver. get_order_status já a inclui "
            "em previous_conversation: continue dela, sem pedir ao cliente que repita o que já disse."
        ),
    ),
    Tool(
        _register_complaint,
        name="register_complaint",
        description="Use quando o cliente faz uma reclamação, com um resumo do que ele relatou. Devolve o prazo de retorno.",
    ),
    Tool(
        _finish_conversation,
        name="finish_conversation",
        description=(
            'Use assim que o cliente disser que não precisa de mais nada, como "era só isso" ou "não, obrigado". '
            "Chame esta ferramenta de verdade, antes de escrever a despedida."
        ),
    ),
)


TOOL_NAMES = {tool.name for tool in TOOLS}
_BARE_NAME = re.compile(r"[a-z]+_[a-z_]+")


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
        self._agent = PydanticAgent(
            model,
            deps_type=Turn,
            tools=tools,
            capabilities=[Hooks(before_model_request=_only_current_customer)],
        )

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
        session = self._sessions.end(conversation_id)
        if session is not None and session.stored_id is not None:
            with write_connection(self._db_path) as conn:
                close(conn, session.stored_id)

    def _store(self, session: Session) -> None:
        if session.user_id is None:
            return
        with write_connection(self._db_path) as conn:
            session.stored_id = save(
                conn,
                session.stored_id,
                session.user_id,
                session.history,
                known_values(session.customer),
                self._clock(),
            )
            if session.closed:
                close(conn, session.stored_id)

    async def _run(self, conversation_id: str, message: str) -> AgentReply:
        session = self._sessions.get(conversation_id)
        async with session.lock:
            turn = Turn(session, conversation_id, self._db_path, self._settings, self._clock(), len(session.history))
            try:
                async with asyncio.timeout(self._run_limit):
                    result = await self._agent.run(message, message_history=session.history, deps=turn)
            except (ModelAPIError, FallbackExceptionGroup) as error:
                raise ProviderError("no model provider answered") from error
            session.history = result.new_messages() if turn.customer_changed else result.all_messages()
            self._sessions.touch(session)
            self._store(session)
        return AgentReply(clean_answer(result.output), build_details(result.new_messages(), self._primary_model))


def create_store_agent(reply_timeout_seconds: float) -> StoreAgent:
    settings = read_settings()
    model, primary_model = build_model(settings)
    return StoreAgent(
        model,
        primary_model=primary_model,
        settings=settings,
        reply_timeout_seconds=reply_timeout_seconds,
        tools=TOOLS,
    )

