import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.function import FunctionModel

from emporio.agent.store.agent import StoreAgent
from emporio.agent.store.providers import (
    REQUEST_TIMEOUT_SECONDS,
    build_model,
    ollama_client,
    openrouter_client,
)
from emporio.errors import ProviderError

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


def test_providers_do_not_retry_on_their_own():
    model, _ = build_model({**OLLAMA, **OPENROUTER})

    assert [m.client.max_retries for m in model.models] == [0, 0]


@pytest.fixture
def tunnel_down():
    """Answers like Cloudflare does when the tunnel to the self-hosted server is down."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("content-length", 0)))
            self.send_response(530)
            self.send_header("Retry-After", "120")
            self.send_header("Content-Type", "text/plain; charset=UTF-8")
            self.end_headers()
            self.wfile.write(b"error code: 1033")

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_a_tunnel_error_fails_fast_instead_of_waiting_for_a_retry(tunnel_down):
    model, primary = build_model({**OLLAMA, "OLLAMA_BASE_URL": tunnel_down})
    agent = StoreAgent(model, primary_model=primary, settings={}, reply_timeout_seconds=60)

    started = time.monotonic()
    with pytest.raises(ProviderError):
        agent.respond("c1", "oi")

    assert time.monotonic() - started < 5


def test_a_tunnel_error_moves_on_to_the_fallback(tunnel_down):
    primary, _ = build_model({**OLLAMA, "OLLAMA_BASE_URL": tunnel_down})
    backup = FunctionModel(lambda _messages, _info: ModelResponse(parts=[TextPart("resposta")]), model_name="backup")
    agent = StoreAgent(FallbackModel(primary, backup), primary_model="chat-local", settings={}, reply_timeout_seconds=60)

    started = time.monotonic()
    reply = agent.respond("c1", "oi")

    assert time.monotonic() - started < 5
    assert reply.answer == "resposta"
    assert reply.details.fallback_used is True

