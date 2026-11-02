import pytest

from emporio.agent.factory import AGENTS, create_agent
from emporio.agent.stand_in import StandInAgent
from emporio.config import Settings, load_settings
from emporio.errors import ConfigError


def test_defaults():
    assert load_settings({}) == Settings(agent="store", troubleshooting=False, reply_timeout_seconds=60)


def test_valid_values():
    settings = load_settings(
        {
            "EMPORIO_AGENT": "stand_in",
            "EMPORIO_TROUBLESHOOTING": "1",
            "EMPORIO_REPLY_TIMEOUT_SECONDS": "2.5",
        }
    )

    assert settings == Settings(agent="stand_in", troubleshooting=True, reply_timeout_seconds=2.5)


def test_blank_values_use_the_defaults():
    settings = load_settings({"EMPORIO_TROUBLESHOOTING": " ", "EMPORIO_REPLY_TIMEOUT_SECONDS": ""})

    assert settings == Settings(agent="store", troubleshooting=False, reply_timeout_seconds=60)


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("EMPORIO_TROUBLESHOOTING", "true"),
        ("EMPORIO_TROUBLESHOOTING", "2"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "soon"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "0"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "-1"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "nan"),
        ("EMPORIO_REPLY_TIMEOUT_SECONDS", "inf"),
    ],
)
def test_invalid_values_name_the_setting_without_the_value(setting, value):
    with pytest.raises(ConfigError) as error:
        load_settings({setting: value})

    assert error.value.setting == setting
    assert setting in str(error.value)
    assert value not in str(error.value)


def test_stand_in_is_selected_by_name():
    agent = create_agent(load_settings({"EMPORIO_AGENT": "stand_in"}))

    assert isinstance(agent, StandInAgent)


def test_stand_in_slow_reply_outlasts_the_reply_limit():
    agent = create_agent(load_settings({"EMPORIO_AGENT": "stand_in", "EMPORIO_REPLY_TIMEOUT_SECONDS": "2"}))

    assert agent._slow_seconds > 2


def test_unknown_agent_is_a_configuration_error_without_a_fallback():
    with pytest.raises(ConfigError) as error:
        create_agent(Settings(agent="planted-unknown", troubleshooting=False, reply_timeout_seconds=60))

    assert error.value.setting == "EMPORIO_AGENT"
    assert "planted-unknown" not in str(error.value)


def test_agent_that_cannot_start_is_a_configuration_error(monkeypatch):
    def fail_to_start(_settings):
        raise RuntimeError("planted-startup-detail")

    monkeypatch.setitem(AGENTS, "broken", fail_to_start)

    with pytest.raises(ConfigError) as error:
        create_agent(Settings(agent="broken", troubleshooting=False, reply_timeout_seconds=60))

    assert error.value.setting == "EMPORIO_AGENT"
    assert "planted-startup-detail" not in str(error.value)


def test_store_agent_without_a_provider_is_a_configuration_error(monkeypatch):
    monkeypatch.setattr("emporio.agent.store.agent.read_settings", lambda: {})

    with pytest.raises(ConfigError) as error:
        create_agent(Settings(agent="store", troubleshooting=False, reply_timeout_seconds=60))

    assert error.value.setting == "EMPORIO_AGENT"

