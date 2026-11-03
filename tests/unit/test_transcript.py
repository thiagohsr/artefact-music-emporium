from datetime import UTC, datetime, timedelta

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from emporio.agent.store.transcript import MAX_RESULT_CHARS, render_turn

START = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


def at(seconds):
    return START + timedelta(seconds=seconds)


def request(seconds, *parts):
    return ModelRequest(parts=list(parts), timestamp=at(seconds))


def response(seconds, *parts, tokens=(100, 10)):
    return ModelResponse(
        parts=list(parts),
        usage=RequestUsage(input_tokens=tokens[0], output_tokens=tokens[1]),
        model_name="qwen3:8b",
        timestamp=at(seconds),
    )


def conversation(returned=None):
    returned = returned or ToolReturnPart("get_product", {"price_brl": 2199.0}, tool_call_id="1", timestamp=at(3.002))
    return [
        request(0, UserPromptPart("Quanto custa?", timestamp=at(0))),
        response(3, ThinkingPart("Preciso consultar."), ToolCallPart("get_product", {"name": "GD20"}, tool_call_id="1")),
        request(3.002, returned),
        response(5.5, TextPart("Custa R$ 2.199,00."), tokens=(1500, 20)),
    ]


def test_the_conversation_comes_first_and_the_details_are_collapsed():
    text = render_turn(conversation(), "qwen3:8b")

    assert text.index("**Cliente:** Quanto custa?") < text.index("**Agente:** Custa R$ 2.199,00.") < text.index("<details>")
    assert text.endswith("</details>")


def test_the_summary_counts_tools_time_and_tokens():
    assert "<summary>Como foi produzida (1 ferramenta, 5,5 s, 1.630 tokens)</summary>" in render_turn(conversation(), "qwen3:8b")


def test_each_model_call_shows_its_time_and_tokens():
    text = render_turn(conversation(), "qwen3:8b")

    assert "**1. Modelo** (3,0 s · 100 tokens de entrada, 10 de saída)" in text
    assert "**2. Modelo** (2,5 s · 1.500 tokens de entrada, 20 de saída)" in text


def test_a_tool_call_shows_its_arguments_and_its_result_with_the_time_it_took():
    text = render_turn(conversation(), "qwen3:8b")

    assert "Chamou `get_product`:" in text
    assert '"name": "GD20"' in text
    assert "Resultado (2 ms):" in text
    assert '"price_brl": 2199.0' in text


def test_the_reasoning_is_shown():
    assert "Preciso consultar." in render_turn(conversation(), "qwen3:8b")


def test_refused_arguments_are_marked_as_a_retry():
    retry = ToolReturnPart("get_product", [{"msg": "Field required"}], tool_call_id="1", timestamp=at(3.002), outcome="retried")

    assert "Argumentos recusados, o modelo tentou de novo" in render_turn(conversation(retry), "qwen3:8b")


def test_a_long_result_is_cut():
    long = ToolReturnPart("get_product", {"text": "x" * (MAX_RESULT_CHARS * 2)}, tool_call_id="1", timestamp=at(3.002))
    text = render_turn(conversation(long), "qwen3:8b")

    assert "[...cortado...]" in text
    assert len(text) < MAX_RESULT_CHARS * 2


def test_a_reply_from_the_fallback_says_so():
    assert "**Modelo:** qwen3:8b (fallback)" in render_turn(conversation(), "qwen3:8b", fallback_used=True)


def test_a_reply_without_tools_says_so():
    messages = [request(0, UserPromptPart("Oi", timestamp=at(0))), response(1, TextPart("Olá!"))]

    assert "(sem ferramentas, 1,0 s, 110 tokens)" in render_turn(messages, "qwen3:8b")


def test_messages_without_timestamps_or_usage_still_render():
    messages = [ModelRequest(parts=[UserPromptPart("Oi")]), ModelResponse(parts=[TextPart("Olá!")])]

    text = render_turn(messages, None)

    assert "**Modelo:** não informado" in text
    assert "**Agente:** Olá!" in text
