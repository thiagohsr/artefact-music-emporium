import contextlib
import logging
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from emporio.data.policy_index import (
    INDEX_PATH,
    embed_with_ollama,
    embed_with_openrouter,
    is_compatible,
    ollama_embedding_model,
    openrouter_embedding_model,
    search_keywords,
    search_vectors,
)

EMBEDDING_TIMEOUT_SECONDS = 10
RESULTS = 3

logger = logging.getLogger(__name__)


def _embedders(settings: Mapping[str, str]) -> list[tuple[Any, str]]:
    embedders = []
    if settings.get("OLLAMA_BASE_URL"):
        embedders.append((embed_with_ollama, ollama_embedding_model(settings)))
    if settings.get("OPENROUTER_API_KEY"):
        embedders.append((embed_with_openrouter, openrouter_embedding_model(settings)))
    return embedders


def policy_lookup(question: str, settings: Mapping[str, str], index_path: Path = INDEX_PATH) -> dict[str, Any]:
    with contextlib.closing(sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)) as conn:
        matches, method = None, "keywords"
        for embed, model in _embedders(settings):
            if not is_compatible(conn, model):
                continue
            try:
                vector = embed([question], settings, EMBEDDING_TIMEOUT_SECONDS)[0]
            except OSError as error:
                logger.warning("Embedding failed, trying the next option: %s", type(error).__name__)
                continue
            matches, method = search_vectors(conn, vector, RESULTS), "vectors"
            break
        if matches is None:
            matches = search_keywords(conn, question, RESULTS)
    return {
        "method": method,
        "sections": [{"number": m.number, "title": m.title, "text": m.body} for m in matches],
    }
