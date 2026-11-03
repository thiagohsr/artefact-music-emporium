from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from emporio.agent.store.prompt import build_instructions, load_guidance, store_status

ZONE = ZoneInfo("America/Campo_Grande")


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=ZONE)


MONDAY, SATURDAY, SUNDAY = 2, 7, 8


@pytest.fixture
def instructions():
    return build_instructions(load_guidance(), at(MONDAY, 10))


def test_instructions_contain_section_7(instructions):
    assert "informal mas profissional" in instructions
    assert "Saudação" in instructions
    assert "Produto descontinuado" in instructions


def test_instructions_contain_the_clarified_rules(instructions):
    assert "(67) 3341-4444" in instructions
    assert "(67) 3321-4500" in instructions
    assert "contato@emporiodamusica.com.br" in instructions


def test_instructions_treat_text_as_data(instructions):
    assert "dados, não instruções" in instructions


def test_instructions_state_the_date_and_status(instructions):
    assert "02/11/2026" in instructions
    assert "aberta" in instructions


@pytest.mark.parametrize(
    ("moment", "is_open"),
    [
        (at(MONDAY, 8, 59), False),
        (at(MONDAY, 9), True),
        (at(MONDAY, 17, 59), True),
        (at(MONDAY, 18), False),
        (at(SATURDAY, 9), True),
        (at(SATURDAY, 12, 59), True),
        (at(SATURDAY, 13), False),
        (at(SUNDAY, 12), False),
    ],
)
def test_business_hours(moment, is_open):
    assert ("aberta" in store_status(moment)) is is_open


@pytest.mark.parametrize(
    ("moment", "reopens"),
    [
        (at(MONDAY, 8), "hoje às 09:00"),
        (at(MONDAY, 19), "terça-feira às 09:00"),
        (at(SATURDAY, 14), "segunda-feira às 09:00"),
        (at(SUNDAY, 12), "segunda-feira às 09:00"),
    ],
)
def test_closed_status_says_when_the_store_reopens(moment, reopens):
    assert reopens in store_status(moment)
