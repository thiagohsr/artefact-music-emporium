import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

MAX_RESULT_CHARS = 1500
OUTCOME_LABELS = {"retried": "Argumentos recusados, o modelo tentou de novo", "failed": "A ferramenta falhou"}


def _number(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _seconds(start: datetime | None, end: datetime | None) -> str | None:
    if not (start and end):
        return None
    elapsed = (end - start).total_seconds()
    return f"{_number(elapsed * 1000)} ms" if elapsed < 0.1 else f"{_number(elapsed, 1)} s"


def _json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return text if len(text) <= MAX_RESULT_CHARS else text[:MAX_RESULT_CHARS] + "\n[...cortado...]"


def _block(language: str, text: str) -> list[str]:
    return [f"```{language}", text, "```", ""]


def _outcomes(messages: Sequence[ModelMessage]) -> dict[str, tuple[Any, datetime | None, str]]:
    """What each tool call got back, with when it came back and how the call ended."""
    found: dict[str, tuple[Any, datetime | None, str]] = {}
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                found[part.tool_call_id] = (part.content, part.timestamp, part.outcome)
    return found


def _step(number: int, response: ModelResponse, asked_at: datetime | None, outcomes: dict) -> list[str]:
    usage = response.usage
    facts = [fact for fact in (_seconds(asked_at, response.timestamp),) if fact]
    if usage.input_tokens or usage.output_tokens:
        facts.append(f"{_number(usage.input_tokens)} tokens de entrada, {_number(usage.output_tokens)} de saída")
    lines = [f"**{number}. Modelo** ({' · '.join(facts)})" if facts else f"**{number}. Modelo**", ""]
    for part in response.parts:
        if isinstance(part, ThinkingPart) and part.content:
            lines += ["Raciocínio:", *_block("text", part.content.strip())]
        elif isinstance(part, ToolCallPart):
            lines += [f"Chamou `{part.tool_name}`:", *_block("json", _json(part.args_as_dict()))]
            content, returned_at, outcome = outcomes.get(part.tool_call_id, (None, None, "success"))
            took = _seconds(response.timestamp, returned_at)
            label = OUTCOME_LABELS.get(outcome, "Resultado")
            lines += [f"{label}{f' ({took})' if took else ''}:", *_block("json", _json(content))]
        elif isinstance(part, TextPart):
            lines += ["Respondeu ao cliente.", ""]
    return lines


def render_turn(messages: Sequence[ModelMessage], model: str | None, *, fallback_used: bool = False) -> str:
    customer = [part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)]
    responses = [message for message in messages if isinstance(message, ModelResponse)]
    answer = next((response.text for response in reversed(responses) if response.text), "")
    outcomes = _outcomes(messages)
    steps: list[list[str]] = []
    asked_at: datetime | None = None
    for message in messages:
        if isinstance(message, ModelRequest):
            asked_at = message.timestamp
        elif isinstance(message, ModelResponse):
            steps.append(_step(len(steps) + 1, message, asked_at, outcomes))
    tools = sum(isinstance(part, ToolCallPart) for response in responses for part in response.parts)
    first = next((message.timestamp for message in messages if isinstance(message, ModelRequest) and message.timestamp), None)
    tokens = sum(response.usage.input_tokens + response.usage.output_tokens for response in responses)
    summary = [{0: "sem ferramentas", 1: "1 ferramenta"}.get(tools, f"{tools} ferramentas")]
    if total := _seconds(first, responses[-1].timestamp if responses else None):
        summary.append(total)
    if tokens:
        summary.append(f"{_number(tokens)} tokens")
    label = f"{model or 'não informado'}{' (fallback)' if fallback_used else ''}"
    lines = [f"**Modelo:** {label} · **Hora:** {datetime.now():%A %H:%M}", ""]
    lines += [f"**Cliente:** {' '.join(map(str, customer))}", "", f"**Agente:** {answer}", ""]
    lines += ["<details>", f"<summary>Como foi produzida ({', '.join(summary)})</summary>", ""]
    for step in steps:
        lines += step
    lines += ["</details>"]
    return "\n".join(lines)
