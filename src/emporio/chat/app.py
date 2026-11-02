from dataclasses import dataclass

import streamlit as st

from emporio.agent.contract import Agent
from emporio.agent.factory import create_agent
from emporio.chat.conversation import (
    MAX_MESSAGE_LENGTH,
    Conversation,
    answer_pending,
    new_conversation,
    submit,
)
from emporio.chat.details_view import render_details
from emporio.chat.utils import waiting_message
from emporio.config import Settings, load_settings
from emporio.errors import ConfigError
from emporio.safety.sanitize import Sanitizer, load_private_values


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    agent: Agent
    sanitizer: Sanitizer


@st.cache_resource(show_spinner=False)
def load_runtime() -> Runtime:
    """Runs once per server process, so settings cannot change and all sessions share one agent."""
    settings = load_settings()
    agent = create_agent(settings)
    sanitizer = Sanitizer([*load_private_values(), *getattr(agent, "private_values", ())])
    return Runtime(settings, agent, sanitizer)


def start_new_conversation(conversation: Conversation, agent: Agent) -> None:
    agent.end_conversation(conversation.id)
    st.session_state.conversation = new_conversation()


@st.dialog("Começar uma nova conversa?")
def confirm_new_conversation(conversation: Conversation, agent: Agent) -> None:
    st.text("A conversa atual será encerrada e as mensagens sairão da tela.")
    confirm_column, cancel_column = st.columns(2)
    confirmed = confirm_column.button(
        "Confirmar",
        key="confirm_new_conversation",
        type="primary",
        on_click=start_new_conversation,
        args=(conversation, agent),
    )
    cancelled = cancel_column.button("Cancelar", key="cancel_new_conversation")
    if confirmed or cancelled:
        st.rerun()


def render_header(conversation: Conversation, agent: Agent) -> None:
    st.title("Empório da Música")
    st.caption("Atendimento por mensagem. Pergunte sobre produtos, pedidos e políticas da loja.")
    if st.button("Nova conversa", key="new_conversation", disabled=conversation.state != "idle"):
        confirm_new_conversation(conversation, agent)


def render_turns(conversation: Conversation, *, troubleshooting: bool) -> None:
    for index, turn in enumerate(conversation.turns):
        with st.chat_message("user"):
            st.text(turn.message)
        if turn.outcome is not None:
            with st.chat_message("assistant"):
                st.text(turn.answer)
                if troubleshooting:
                    render_details(turn, index)


def render_rejected_draft(conversation: Conversation) -> None:
    draft = conversation.rejected_draft
    if draft is None:
        return
    limit = f"{MAX_MESSAGE_LENGTH:,}".replace(",", ".")
    st.error(
        f"Sua mensagem tem {len(draft.strip())} caracteres e o limite é de {limit} caracteres. "
        "Edite o texto abaixo para enviar."
    )
    edited = st.text_area("Edite sua mensagem", value=draft, height=200, key=f"draft_{hash(draft)}")
    send_column, discard_column = st.columns(2)
    if send_column.button("Enviar", key="send_draft", type="primary"):
        submit(conversation, edited)
        st.rerun()
    if discard_column.button("Descartar", key="discard_draft"):
        conversation.rejected_draft = None
        st.rerun()


def answer_waiting_turn(conversation: Conversation, runtime: Runtime) -> None:
    with st.chat_message("assistant"):
        # st.spinner cannot change its text once started, and st.status can.
        shown_message = waiting_message(0)
        status = st.status(shown_message)

        def show_progress(elapsed_seconds: float) -> None:
            nonlocal shown_message
            message = waiting_message(elapsed_seconds)
            if message != shown_message:
                status.update(label=message)
                shown_message = message

        answer_pending(
            conversation,
            runtime.agent,
            runtime.sanitizer,
            timeout_seconds=runtime.settings.reply_timeout_seconds,
            keep_details=runtime.settings.troubleshooting,
            on_wait=show_progress,
        )
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Empório da Música")
    try:
        runtime = load_runtime()
    except ConfigError as error:
        st.title("Empório da Música")
        st.error(f"The application could not start. Check this setting. {error}")
        st.stop()
    if "conversation" not in st.session_state:
        st.session_state.conversation = new_conversation()
    conversation: Conversation = st.session_state.conversation
    waiting = conversation.state == "waiting"

    render_header(conversation, runtime.agent)
    if runtime.agent.is_simulated:
        st.info("As respostas são simuladas e não vêm do assistente real.")
    render_turns(conversation, troubleshooting=runtime.settings.troubleshooting)
    render_rejected_draft(conversation)

    # The disabled input must reach the page before the agent call begins (FR-005).
    message = st.chat_input("Digite sua mensagem", disabled=waiting)
    if waiting:
        answer_waiting_turn(conversation, runtime)
    if message is not None:
        submit(conversation, message)
        st.rerun()


main()
