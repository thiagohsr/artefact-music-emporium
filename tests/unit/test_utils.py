import pytest

from emporio.chat.utils import WAITING_MESSAGES, waiting_message


def test_first_message_is_the_preparing_message():
    assert waiting_message(0) == "Preparando sua resposta..."


@pytest.mark.parametrize(("seconds", "message"), WAITING_MESSAGES)
def test_each_message_starts_at_its_threshold(seconds, message):
    assert waiting_message(seconds) == message


def test_message_stays_until_the_next_threshold():
    (_, first), (second_start, _) = WAITING_MESSAGES[:2]

    assert waiting_message(second_start - 0.01) == first


def test_last_message_stays_after_its_threshold():
    last_start, last = WAITING_MESSAGES[-1]

    assert waiting_message(last_start + 1000) == last


def test_thresholds_are_in_order_with_distinct_messages():
    seconds = [start for start, _ in WAITING_MESSAGES]
    messages = [message for _, message in WAITING_MESSAGES]

    assert seconds == sorted(seconds)
    assert seconds[0] == 0
    assert len(set(messages)) == len(messages)
