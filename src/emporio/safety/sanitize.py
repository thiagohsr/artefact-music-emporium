import dataclasses
import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv

REDACTED = "[REMOVIDO]"
MIN_PRIVATE_VALUE_LENGTH = 8

_SENSITIVE_NAME = re.compile(r"(?i)api[_-]?key|secret|password|passwd|token|authorization|credential|client_id")
_NON_SECRET_NAME = re.compile(r"MODEL|^EMPORIO_")


class Sanitizer:
    def __init__(self, private_values: Iterable[str] = ()) -> None:
        self._private_values = sorted(set(private_values), key=len, reverse=True)

    def text(self, value: str) -> str:
        for private_value in self._private_values:
            value = value.replace(private_value, REDACTED)
        return value

    def value(self, value: Any) -> Any:
        if value is None or isinstance(value, bool | int | float):
            return value
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            return {self.text(str(key)): self._mapping_item(key, item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return type(value)(self.value(item) for item in value)
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            fields = {field.name: self.value(getattr(value, field.name)) for field in dataclasses.fields(value)}
            return dataclasses.replace(value, **fields)
        return self.text(str(value))

    def _mapping_item(self, key: Any, item: Any) -> Any:
        if isinstance(item, str) and _SENSITIVE_NAME.search(str(key)):
            return REDACTED
        return self.value(item)


def load_private_values(
    environ: Mapping[str, str] | None = None,
    env_file: str | Path | None = None,
) -> list[str]:
    environ = os.environ if environ is None else environ
    env_file = find_dotenv(usecwd=True) if env_file is None else env_file
    candidates = dict(dotenv_values(env_file)) if env_file else {}
    candidates |= {name: value for name, value in environ.items() if _SENSITIVE_NAME.search(name)}
    return [
        value
        for name, value in candidates.items()
        if value and len(value) >= MIN_PRIVATE_VALUE_LENGTH and not _NON_SECRET_NAME.search(name)
    ]
