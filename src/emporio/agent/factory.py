from collections.abc import Callable

from emporio.agent.contract import Agent
from emporio.agent.stand_in import StandInAgent
from emporio.config import Settings
from emporio.errors import ConfigError

SLOW_REPLY_MARGIN_SECONDS = 5


def _create_stand_in(settings: Settings) -> Agent:
    return StandInAgent(slow_seconds=settings.reply_timeout_seconds + SLOW_REPLY_MARGIN_SECONDS)


AGENTS: dict[str, Callable[[Settings], Agent]] = {"stand_in": _create_stand_in}


def create_agent(settings: Settings) -> Agent:
    create = AGENTS.get(settings.agent)
    if create is None:
        raise ConfigError("EMPORIO_AGENT", "is not a known agent")
    try:
        return create(settings)
    except ConfigError:
        raise
    except Exception:
        raise ConfigError("EMPORIO_AGENT", "the selected agent could not start") from None
