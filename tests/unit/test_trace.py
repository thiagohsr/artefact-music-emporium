from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from emporio.agent.contract import is_valid_details
from emporio.agent.store.trace import build_details


def run(*parts, tool_returns=(), model_name="primary"):
    return [
        ModelRequest(parts=[UserPromptPart("Oi")]),
        ModelResponse(parts=list(parts), model_name=model_name, provider_name="provider"),
        ModelRequest(parts=list(tool_returns)),
        ModelResponse(parts=[TextPart("Resposta")], model_name=model_name, provider_name="provider"),
    ]


def call(name, args, call_id="1"):
    return ToolCallPart(name, args, tool_call_id=call_id)


def result(name, content, call_id="1"):
    return ToolReturnPart(name, content, tool_call_id=call_id)


def test_tool_call_and_result_become_a_step():
    details = build_details(
        run(call("get_product", {"name": "Takamine"}), tool_returns=[result("get_product", {"found": True})]), "primary"
    )

    step = details.steps[0]
    assert (step.name, step.kind, step.status) == ("get_product", "tool", "ok")
    assert step.inputs == {"name": "Takamine"}
    assert step.result == {"found": True}
    assert is_valid_details(details)


def test_policy_lookup_is_retrieval_with_policy_sources():
    sections = {"sections": [{"number": "4.1", "title": "Direito de Arrependimento", "text": "..."}]}

    details = build_details(run(call("policy_lookup", {"question": "?"}), tool_returns=[result("policy_lookup", sections)]), "primary")

    assert details.steps[0].kind == "retrieval"
    assert [(s.kind, s.name) for s in details.sources] == [("policy", "4.1 Direito de Arrependimento")]


def test_store_tools_give_data_sources():
    details = build_details(
        run(
            call("search_products", {}, "1"),
            call("get_order_status", {}, "2"),
            call("payment_terms", {}, "3"),
            tool_returns=[result("search_products", {}, "1"), result("get_order_status", {}, "2"), result("payment_terms", {}, "3")],
        ),
        "primary",
    )

    assert [(s.kind, s.name) for s in details.sources] == [("data", "products"), ("data", "orders")]


def test_same_source_is_listed_once():
    details = build_details(
        run(call("get_product", {}, "1"), call("search_products", {}, "2"), tool_returns=[result("get_product", {}, "1"), result("search_products", {}, "2")]),
        "primary",
    )

    assert len(details.sources) == 1


def test_thinking_becomes_a_reasoning_step():
    details = build_details(run(ThinkingPart("Pensando"), call("get_product", {}), tool_returns=[result("get_product", {})]), "primary")

    assert [(s.kind, s.result) for s in details.steps][0] == ("reasoning", "Pensando")


def test_model_and_provider_come_from_the_answering_response():
    details = build_details(run(TextPart("x")), "primary")

    assert (details.model, details.provider, details.fallback_used) == ("primary", "provider", False)


def test_fallback_is_reported_when_another_model_answered():
    details = build_details(run(TextPart("x"), model_name="backup"), "primary")

    assert details.model == "backup"
    assert details.fallback_used is True


def test_call_without_a_result_is_an_error_step():
    assert build_details(run(call("get_product", {})), "primary").steps[0].status == "error"
