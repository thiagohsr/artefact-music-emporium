import contextlib
import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from build_policy_index import PDF_PATH, parse_sections
from pypdf import PdfReader

from emporio.data.policy_index import (
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OPENROUTER_EMBEDDING_MODEL,
    INDEX_PATH,
    decode_vector,
    embed_with_ollama,
    is_compatible,
    ollama_embedding_model,
    openrouter_embedding_model,
    search_keywords,
    search_vectors,
)


@pytest.fixture
def conn():
    with contextlib.closing(sqlite3.connect(f"file:{INDEX_PATH}?mode=ro", uri=True)) as connection:
        yield connection


def numbers(conn, audience):
    rows = conn.execute("SELECT number FROM policy_sections WHERE audience = ?", (audience,))
    return {number for number, in rows}


def test_numbered_lists_are_not_read_as_headings():
    sections = parse_sections(["1. Primeira\ntexto\n1.1 Sub\n1. item\n5. item\n2. Segunda\nfim"])

    assert [section.number for section in sections] == ["1", "1.1", "2"]
    assert sections[1].lines == ["1. item", "5. item"]


def test_the_manual_parses_into_all_its_sections():
    sections = parse_sections([page.extract_text(extraction_mode="layout") for page in PdfReader(PDF_PATH).pages])

    assert len(sections) == 28
    assert sections[-1].number == "10"


def test_running_headers_and_page_markers_are_removed():
    sections = parse_sections(["1. Primeira\nantes\nPágina 3\nEmpório da Música Manual de Políticas e Procedimentos\ndepois"])

    assert sections[0].lines == ["antes", "depois"]


def test_index_matches_the_committed_pdf(conn):
    stored = dict(conn.execute("SELECT key, value FROM index_metadata"))

    assert stored["source_sha256"] == hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()


def test_vectors_have_the_recorded_dimensions(conn):
    dimensions = int(dict(conn.execute("SELECT key, value FROM index_metadata"))["dimensions"])

    for blob, in conn.execute("SELECT embedding FROM policy_vectors"):
        assert len(decode_vector(blob)) == dimensions


def test_staff_sections_are_tagged(conn):
    assert numbers(conn, "staff") == {"7", "7.1", "7.2", "7.3", "10"}


def test_grouping_sections_are_not_searchable(conn):
    searchable = {number for number, in conn.execute("SELECT number FROM policy_vectors")}

    assert searchable.isdisjoint({"5", "6", "8"})


def test_vector_search_returns_only_customer_sections(conn):
    blob, = conn.execute("SELECT embedding FROM policy_vectors WHERE number = '7.1'").fetchone()

    matches = search_vectors(conn, decode_vector(blob), limit=30)

    assert matches
    assert {match.number for match in matches}.isdisjoint(numbers(conn, "staff"))


def test_vector_search_finds_a_section_from_its_own_vector(conn):
    blob, = conn.execute("SELECT embedding FROM policy_vectors WHERE number = '4.1'").fetchone()

    assert search_vectors(conn, decode_vector(blob))[0].number == "4.1"


def test_keyword_search_ignores_accents(conn):
    assert search_keywords(conn, "arrependimento")[0].number == "4.1"
    assert search_keywords(conn, "manutencao") == search_keywords(conn, "manutenção")


def test_keyword_search_skips_staff_sections(conn):
    assert {match.number for match in search_keywords(conn, "atendente saudação", limit=30)}.isdisjoint(
        numbers(conn, "staff")
    )


def test_question_without_searchable_words_returns_nothing(conn):
    assert search_keywords(conn, "?!") == []


@pytest.mark.parametrize("model", [DEFAULT_OLLAMA_EMBEDDING_MODEL, DEFAULT_OPENROUTER_EMBEDDING_MODEL])
def test_both_names_of_the_building_model_are_compatible(conn, model):
    assert is_compatible(conn, model)


def test_another_model_is_not_compatible(conn):
    assert not is_compatible(conn, "another-embedding-model")


def test_embedding_models_default_when_unset_or_blank():
    assert ollama_embedding_model({}) == DEFAULT_OLLAMA_EMBEDDING_MODEL
    assert ollama_embedding_model({"OLLAMA_EMBEDDING_MODEL": ""}) == DEFAULT_OLLAMA_EMBEDDING_MODEL
    assert openrouter_embedding_model({}) == DEFAULT_OPENROUTER_EMBEDDING_MODEL


def test_configured_embedding_model_is_sent_to_the_provider(monkeypatch):
    sent = []

    def fake_post(_url, payload, _headers, _timeout_seconds):
        sent.append(payload["model"])
        return {"embeddings": [[1.0]]}

    monkeypatch.setattr("emporio.data.policy_index._post", fake_post)

    embed_with_ollama(["texto"], {"OLLAMA_BASE_URL": "http://local", "OLLAMA_EMBEDDING_MODEL": "outro"})

    assert sent == ["outro"]
