import logging
from collections.abc import Callable

from emporio.agent.contract import Agent
from emporio.agent.stand_in import StandInAgent
from emporio.config import Settings
from emporio.errors import ConfigError
from emporio.safety.sanitize import Sanitizer, load_private_values

SLOW_REPLY_MARGIN_SECONDS = 5

logger = logging.getLogger(__name__)


def _create_stand_in(settings: Settings) -> Agent:
    return StandInAgent(slow_seconds=settings.reply_timeout_seconds + SLOW_REPLY_MARGIN_SECONDS)


def _create_store(settings: Settings) -> Agent:
    from emporio.agent.store.agent import create_store_agent

    return create_store_agent(settings.reply_timeout_seconds)


AGENTS: dict[str, Callable[[Settings], Agent]] = {"stand_in": _create_stand_in, "store": _create_store}


def create_agent(settings: Settings) -> Agent:
    create = AGENTS.get(settings.agent)
    if create is None:
        raise ConfigError("EMPORIO_AGENT", "is not a known agent")
    try:
        return create(settings)
    except ConfigError:
        raise
    except Exception as error:  # noqa: BLE001 - any startup failure must become a clean settings error
        logger.error("Agent %s could not start:\n%s", settings.agent, Sanitizer(load_private_values()).exception(error))
        raise ConfigError("EMPORIO_AGENT", "the selected agent could not start") from None
