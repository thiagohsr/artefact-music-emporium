import json
import re
from typing import Any

import streamlit as st

from emporio.agent.contract import ReplyDetails, Step
from emporio.chat.conversation import Turn

MAX_INLINE_STEPS = 10
MAX_INLINE_CHARACTERS = 6000
MAX_VALUE_CHARACTERS = 2000
SHORTENED_MARKER = "\n... [shortened, open the full details to see the rest]"

_MARKDOWN_CHARACTERS = re.compile(r"([\\`*_{}\[\]()#+\-.!~$:<>|])")


def _plain_label(text: str) -> str:
    """Expander labels render Markdown, so step names are escaped to stay plain content."""
    return _MARKDOWN_CHARACTERS.sub(r"\\\1", text)


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _step_values(step: Step) -> list[tuple[str, str]]:
    values = [("Inputs", step.inputs), ("Result", step.result), ("Error", step.error)]
    return [(label, _as_text(value)) for label, value in values if value not in (None, "", {}, [], ())]


def _all_values(details: ReplyDetails) -> list[str]:
    return [text for step in details.steps for _, text in _step_values(step)]


def _is_too_large_for_inline(details: ReplyDetails) -> bool:
    return len(details.steps) > MAX_INLINE_STEPS or sum(map(len, _all_values(details))) > MAX_INLINE_CHARACTERS


def _has_long_value(details: ReplyDetails) -> bool:
    return any(len(text) > MAX_VALUE_CHARACTERS for text in _all_values(details))


def _step_label(number: int, step: Step) -> str:
    parts = [f"{number}. {step.name}", step.kind, step.status]
    if step.duration_ms is not None:
        parts.append(f"{step.duration_ms:g} ms")
    return _plain_label(" | ".join(parts))


def _render_step(number: int, step: Step, *, shorten: bool) -> None:
    with st.expander(_step_label(number, step)):
        for label, text in _step_values(step):
            if shorten and len(text) > MAX_VALUE_CHARACTERS:
                text = text[:MAX_VALUE_CHARACTERS] + SHORTENED_MARKER
            st.text(label)
            st.code(text, language=None, wrap_lines=True)


def _render_summary(turn: Turn) -> None:
    details = turn.details
    st.text(f"Outcome: {turn.outcome}")
    st.text(f"Details: {turn.details_state}")
    st.text(f"Total time: {turn.elapsed_ms:.0f} ms")
    if details is None:
        return
    st.text(f"Model: {details.model or 'not reported'}")
    st.text(f"Provider: {details.provider or 'not reported'}")
    st.text(f"Fallback used: {'yes' if details.fallback_used else 'no'}")
    if details.sources:
        st.text("Sources: " + ", ".join(f"{source.kind}: {source.name}" for source in details.sources))
    else:
        st.text("No sources were used.")
    if not details.steps and turn.details_state == "complete":
        st.text("No tools or other steps were used.")
    for error in details.errors:
        st.text(f"Error: {error}")


@st.dialog("Full reply details", width="large")
def _show_full_details(details: ReplyDetails) -> None:
    for number, step in enumerate(details.steps, start=1):
        _render_step(number, step, shorten=False)


def render_details(turn: Turn, turn_index: int) -> None:
    details = turn.details
    with st.expander("Reply details"):
        _render_summary(turn)
        if details is None:
            return
        too_large = _is_too_large_for_inline(details)
        if not too_large:
            for number, step in enumerate(details.steps, start=1):
                _render_step(number, step, shorten=True)
        if too_large or _has_long_value(details):
            if st.button("Open full details", key=f"open_details_{turn_index}"):
                _show_full_details(details)
