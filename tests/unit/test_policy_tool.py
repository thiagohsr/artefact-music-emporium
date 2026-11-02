import pytest

from emporio.tools.policies import policy_lookup

STAFF = {"7", "7.1", "7.2", "7.3", "10"}


def fake_embed(_texts, _settings, timeout_seconds):
    import contextlib
    import sqlite3

    from emporio.data.policy_index import INDEX_PATH, decode_vector

    with contextlib.closing(sqlite3.connect(INDEX_PATH)) as conn:
        return [list(decode_vector(conn.execute("SELECT embedding FROM policy_vectors WHERE number = '4.1'").fetchone()[0]))]


@pytest.fixture
def ollama(monkeypatch):
    monkeypatch.setattr("emporio.tools.policies.embed_with_ollama", fake_embed)
    return {"OLLAMA_BASE_URL": "http://local"}


def test_returns_up_to_three_sections_with_numbers(ollama):
    result = policy_lookup("posso devolver?", ollama)

    assert len(result["sections"]) == 3
    assert result["sections"][0]["number"] == "4.1"
    assert result["sections"][0]["title"]
    assert "7 (sete) dias" in result["sections"][0]["text"]
    assert result["method"] == "vectors"


def test_staff_sections_are_never_returned(ollama):
    assert not {s["number"] for s in policy_lookup("tom de voz atendimento", ollama)["sections"]} & STAFF
    assert not {s["number"] for s in policy_lookup("tom de voz atendimento", {})["sections"]} & STAFF


def test_no_provider_falls_back_to_keywords():
    result = policy_lookup("arrependimento", {})

    assert result["method"] == "keywords"
    assert result["sections"][0]["number"] == "4.1"


def test_failed_embedding_falls_back_to_keywords(monkeypatch, ollama):
    def fail(*_args):
        raise OSError("server down")

    monkeypatch.setattr("emporio.tools.policies.embed_with_ollama", fail)

    assert policy_lookup("arrependimento", ollama)["method"] == "keywords"


def test_next_provider_is_tried_when_the_first_fails(monkeypatch, ollama):
    def fail(*_args):
        raise OSError("server down")

    monkeypatch.setattr("emporio.tools.policies.embed_with_ollama", fail)
    monkeypatch.setattr("emporio.tools.policies.embed_with_openrouter", fake_embed)

    result = policy_lookup("posso devolver?", {**ollama, "OPENROUTER_API_KEY": "key"})

    assert result["method"] == "vectors"


def test_incompatible_embedding_model_falls_back_to_keywords(monkeypatch, ollama):
    called = []
    monkeypatch.setattr("emporio.tools.policies.embed_with_ollama", lambda *a: called.append(a))

    result = policy_lookup("arrependimento", {**ollama, "OLLAMA_EMBEDDING_MODEL": "another-model"})

    assert result["method"] == "keywords"
    assert called == []
