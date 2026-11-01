import array
import json
import math
import os
import re
import sqlite3
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, find_dotenv

INDEX_PATH = Path(__file__).resolve().parents[3] / "data" / "policies.sqlite"
DEFAULT_OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:4b"
DEFAULT_OPENROUTER_EMBEDDING_MODEL = "qwen/qwen3-embedding-4b"
# One model under each provider's name: in tests their vectors for the same text had a cosine of about 0.98
# and ranked sections alike, so an index built on one answers questions embedded on the other.
EQUIVALENT_MODELS = {DEFAULT_OLLAMA_EMBEDDING_MODEL, DEFAULT_OPENROUTER_EMBEDDING_MODEL}
OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings"
REQUEST_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class Match:
    number: str
    title: str
    body: str
    score: float


def read_settings() -> dict[str, str]:
    return {**dotenv_values(find_dotenv(usecwd=True)), **os.environ}


def _post(url: str, payload: dict, headers: Mapping[str, str]) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "artefact-music-emporium", **headers},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def ollama_embedding_model(settings: Mapping[str, str]) -> str:
    return settings.get("OLLAMA_EMBEDDING_MODEL") or DEFAULT_OLLAMA_EMBEDDING_MODEL


def openrouter_embedding_model(settings: Mapping[str, str]) -> str:
    return settings.get("OPENROUTER_EMBEDDING_MODEL") or DEFAULT_OPENROUTER_EMBEDDING_MODEL


def embed_with_ollama(texts: Sequence[str], settings: Mapping[str, str]) -> list[list[float]]:
    response = _post(
        f"{settings['OLLAMA_BASE_URL'].rstrip('/')}/api/embed",
        {"model": ollama_embedding_model(settings), "input": list(texts)},
        {
            "CF-Access-Client-Id": settings.get("CF_ACCESS_CLIENT_ID", ""),
            "CF-Access-Client-Secret": settings.get("CF_ACCESS_CLIENT_SECRET", ""),
        },
    )
    return response["embeddings"]


def embed_with_openrouter(texts: Sequence[str], settings: Mapping[str, str]) -> list[list[float]]:
    response = _post(
        OPENROUTER_URL,
        {"model": openrouter_embedding_model(settings), "input": list(texts)},
        {"Authorization": f"Bearer {settings['OPENROUTER_API_KEY']}"},
    )
    return [item["embedding"] for item in sorted(response["data"], key=lambda item: item["index"])]


def encode_vector(vector: Sequence[float]) -> bytes:
    return array.array("f", vector).tobytes()


def decode_vector(blob: bytes) -> array.array:
    vector = array.array("f")
    vector.frombytes(blob)
    return vector


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return dot / (math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right)))


def is_compatible(conn: sqlite3.Connection, model: str) -> bool:
    """Vectors from another model can have the same size, so a mismatch would rank wrongly without any error."""
    built_with = conn.execute("SELECT value FROM index_metadata WHERE key = 'model'").fetchone()[0]
    return model == built_with or {model, built_with} <= EQUIVALENT_MODELS


def search_vectors(conn: sqlite3.Connection, query_vector: Sequence[float], limit: int = 3) -> list[Match]:
    rows = conn.execute(
        """
        SELECT s.number, s.title, s.body, v.embedding
        FROM policy_vectors v JOIN policy_sections s USING (number)
        WHERE s.audience = 'customer'
        """
    )
    matches = [
        Match(number, title, body, _cosine(query_vector, decode_vector(blob)))
        for number, title, body, blob in rows
    ]
    return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]


def search_keywords(conn: sqlite3.Connection, question: str, limit: int = 3) -> list[Match]:
    terms = re.findall(r"\w{3,}", question)
    if not terms:
        return []
    rows = conn.execute(
        """
        SELECT s.number, s.title, s.body, bm25(policy_fts)
        FROM policy_fts JOIN policy_sections s ON s.number = policy_fts.number
        WHERE policy_fts MATCH ? AND s.audience = 'customer'
        ORDER BY bm25(policy_fts)
        LIMIT ?
        """,
        (" OR ".join(f'"{term}"' for term in terms), limit),
    )
    return [Match(number, title, body, -score) for number, title, body, score in rows]
