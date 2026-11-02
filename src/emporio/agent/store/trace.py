from collections.abc import Sequence
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)

from emporio.agent.contract import ReplyDetails, Source, Step

DATA_SOURCES = {"search_products": "products", "get_product": "products", "get_order_status": "orders"}


def _returns(messages: Sequence[ModelMessage]) -> dict[str, Any]:
    return {
        part.tool_call_id: part.content
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    }


def _policy_sources(content: Any) -> list[Source]:
    sections = content.get("sections", []) if isinstance(content, dict) else []
    return [Source("policy", f"{section['number']} {section['title']}") for section in sections]


def build_details(messages: Sequence[ModelMessage], primary_model: str) -> ReplyDetails:
    returns = _returns(messages)
    steps: list[Step] = []
    sources: dict[tuple[str, str], Source] = {}
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        for part in message.parts:
            if isinstance(part, ThinkingPart) and part.content:
                steps.append(Step("thinking", "reasoning", result=part.content))
            elif isinstance(part, ToolCallPart):
                answered = part.tool_call_id in returns
                content = returns.get(part.tool_call_id)
                kind = "retrieval" if part.tool_name == "policy_lookup" else "tool"
                steps.append(
                    Step(
                        part.tool_name,
                        kind,
                        status="ok" if answered else "error",
                        inputs=part.args_as_dict(),
                        result=content,
                    )
                )
                found = _policy_sources(content) if part.tool_name == "policy_lookup" else []
                if part.tool_name in DATA_SOURCES:
                    found = [Source("data", DATA_SOURCES[part.tool_name])]
                sources.update({(source.kind, source.name): source for source in found})
    responses = [message for message in messages if isinstance(message, ModelResponse)]
    last = responses[-1] if responses else None
    return ReplyDetails(
        steps=tuple(steps),
        sources=tuple(sources.values()),
        model=last.model_name if last else None,
        provider=last.provider_name if last else None,
        fallback_used=bool(last and last.model_name != primary_model),
    )
