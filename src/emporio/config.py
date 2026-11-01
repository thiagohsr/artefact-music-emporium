import math
import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

DEFAULT_AGENT = "stand_in"
DEFAULT_REPLY_TIMEOUT_SECONDS = 60.0


class ConfigError(Exception):
    def __init__(self, setting: str, problem: str) -> None:
        super().__init__(f"{setting}: {problem}")
        self.setting = setting


@dataclass(frozen=True)
class Settings:
    agent: str
    troubleshooting: bool
    reply_timeout_seconds: float


def _read_troubleshooting(value: str) -> bool:
    if value not in ("", "0", "1"):
        raise ConfigError("EMPORIO_TROUBLESHOOTING", "must be 0 or 1")
    return value == "1"


def _read_timeout(value: str) -> float:
    if not value:
        return DEFAULT_REPLY_TIMEOUT_SECONDS
    try:
        seconds = float(value)
    except ValueError:
        seconds = math.nan
    if not math.isfinite(seconds) or seconds <= 0:
        raise ConfigError("EMPORIO_REPLY_TIMEOUT_SECONDS", "must be a positive number")
    return seconds


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    if environ is None:
        load_dotenv(find_dotenv(usecwd=True))
        environ = os.environ

    def read(name: str) -> str:
        return environ.get(name, "").strip()

    return Settings(
        agent=read("EMPORIO_AGENT") or DEFAULT_AGENT,
        troubleshooting=_read_troubleshooting(read("EMPORIO_TROUBLESHOOTING")),
        reply_timeout_seconds=_read_timeout(read("EMPORIO_REPLY_TIMEOUT_SECONDS")),
    )
