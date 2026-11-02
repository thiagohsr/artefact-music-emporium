import pytest
from pydantic_ai.models.fallback import FallbackModel

from emporio.agent.store.providers import (
    REQUEST_TIMEOUT_SECONDS,
    build_model,
    ollama_client,
    openrouter_client,
)

OLLAMA = {
    "OLLAMA_BASE_URL": "http://ollama.invalid/",
    "OLLAMA_CHAT_MODEL": "chat-local",
    "CF_ACCESS_CLIENT_ID": "cf-id",
    "CF_ACCESS_CLIENT_SECRET": "cf-secret",
}
OPENROUTER = {"OPENROUTER_API_KEY": "or-key", "OPENROUTER_CHAT_MODEL": "openai/chat-hosted"}


def test_ollama_comes_first_and_openrouter_second():
    model, primary = build_model({**OLLAMA, **OPENROUTER})

    assert isinstance(model, FallbackModel)
    assert [m.model_name for m in model.models] == ["chat-local", "openai/chat-hosted"]
    assert primary == "chat-local"


@pytest.mark.parametrize(("settings", "name"), [(OLLAMA, "chat-local"), (OPENROUTER, "openai/chat-hosted")])
def test_either_provider_alone_works(settings, name):
    model, primary = build_model(settings)

    assert model.model_name == name
    assert primary == name


@pytest.mark.parametrize(
    "settings",
    [{}, {"OLLAMA_BASE_URL": "http://x"}, {"OPENROUTER_API_KEY": "k"}, {"OLLAMA_CHAT_MODEL": "m"}],
)
def test_incomplete_settings_raise(settings):
    with pytest.raises(ValueError):
        build_model(settings)


def test_cloudflare_headers_go_only_on_the_ollama_client():
    assert ollama_client(OLLAMA).headers["CF-Access-Client-Secret"] == "cf-secret"
    assert "CF-Access-Client-Secret" not in openrouter_client().headers


def test_requests_have_the_time_limit():
    assert REQUEST_TIMEOUT_SECONDS == 25
    assert ollama_client(OLLAMA).timeout.read == 25
    assert openrouter_client().timeout.read == 25
