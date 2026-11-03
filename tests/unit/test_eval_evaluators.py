from types import SimpleNamespace

import pytest
from evaluators import CalledTool, NeverSays, Outcome, ReturnedSection, Says

from emporio.agent.contract import Step


def context(answer="Ok", *steps):
    return SimpleNamespace(output=Outcome(answer, tuple(steps), "model", False))


def lookup(*numbers):
    return Step("policy_lookup", "retrieval", inputs={"question": "?"}, result={"sections": [{"number": n} for n in numbers]})


def order(**inputs):
    return Step("get_order_status", "tool", inputs=inputs, result={"verified": True})


def test_a_tool_that_never_ran_fails_both_checks():
    results = CalledTool("get_order_status", {"phone": "1"}).evaluate(context())

    assert results == {"called:get_order_status": False, "arguments:get_order_status": False}


def test_the_phone_matches_by_digits_the_email_ignoring_case_and_the_code_ignoring_separators():
    given = {"tracking_code": "BRKR1122334BR", "phone": "(67) 99789-0123", "email": "Leticia@Jmail.com"}
    ran = order(tracking_code="brkr 1122334 br", phone="67997890123", email="leticia@jmail.com")

    assert CalledTool("get_order_status", given).evaluate(context("", ran))["arguments:get_order_status"] is True


def test_one_wrong_argument_fails():
    ran = order(tracking_code="BRKR1122334BR", phone="(67) 90000-0000", email="a@b.c")

    assert CalledTool("get_order_status", {"phone": "(67) 99789-0123"}).evaluate(context("", ran))["arguments:get_order_status"] is False


def test_the_arguments_must_come_from_a_single_call():
    first, second = order(phone="1", email="x"), order(phone="2", email="y")

    results = CalledTool("get_order_status", {"phone": "1", "email": "y"}).evaluate(context("", first, second))

    assert results["arguments:get_order_status"] is False


@pytest.mark.parametrize(("found", "expected"), [(("4.1", "4.3"), True), (("4.3", "4.4"), False), ((), False)])
def test_a_section_must_be_among_those_the_lookup_returned(found, expected):
    steps = (lookup(*found),) if found else ()

    assert ReturnedSection("4.1").evaluate(context("", *steps)) == {"section 4.1 found": expected}


def test_a_failed_lookup_returning_no_sections_does_not_crash():
    failed = Step("policy_lookup", "retrieval", result=[{"type": "missing"}])

    assert ReturnedSection("4.1").evaluate(context("", failed)) == {"section 4.1 found": False}


def test_says_and_never_says_ignore_case():
    answer = "O PRAZO de 7 dias passou"

    assert Says((r"7 dias",)).evaluate(context(answer)) == {"says:7 dias": True}
    assert NeverSays((r"reembolso",)).evaluate(context(answer)) == {"never:reembolso": True}
    assert NeverSays((r"prazo",)).evaluate(context(answer)) == {"never:prazo": False}
