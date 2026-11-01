from dataclasses import dataclass

import streamlit as st

from emporio.agent.contract import Agent
from emporio.agent.factory import create_agent
from emporio.chat.conversation import MAX_MESSAGE_LENGTH, Conversation, answer_pending, new_conversation, submit
from emporio.config import Settings, load_settings
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


def render_header(conversation: Conversation) -> None:
    st.title("Empório da Música")
    st.caption("Atendimento por mensagem. Pergunte sobre produtos, pedidos e políticas da loja.")
    if st.button("Nova conversa", key="new_conversation", disabled=conversation.state != "idle"):
        st.session_state.conversation = new_conversation()
        st.rerun()


def render_turns(conversation: Conversation) -> None:
    for turn in conversation.turns:
        with st.chat_message("user"):
            st.text(turn.message)
        if turn.outcome is not None:
            with st.chat_message("assistant"):
                st.text(turn.answer)


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
    with st.chat_message("assistant"), st.spinner("Preparando sua resposta..."):
        answer_pending(
            conversation,
            runtime.agent,
            runtime.sanitizer,
            timeout_seconds=runtime.settings.reply_timeout_seconds,
            keep_details=runtime.settings.troubleshooting,
        )
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Empório da Música")
    runtime = load_runtime()
    if "conversation" not in st.session_state:
        st.session_state.conversation = new_conversation()
    conversation: Conversation = st.session_state.conversation
    waiting = conversation.state == "waiting"

    render_header(conversation)
    render_turns(conversation)
    render_rejected_draft(conversation)

    # The disabled input must reach the page before the agent call begins (FR-005).
    message = st.chat_input("Digite sua mensagem", disabled=waiting)
    if waiting:
        answer_waiting_turn(conversation, runtime)
    if message is not None:
        submit(conversation, message)
        st.rerun()


main()
