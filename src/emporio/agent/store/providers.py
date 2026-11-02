from collections.abc import Mapping

import httpx2
from openai import AsyncOpenAI
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

REQUEST_TIMEOUT_SECONDS = 25
# When the tunnel to the self-hosted server is down, Cloudflare answers at once but the SDK obeys its long Retry-After,
# which outlasts a whole reply, so the fallback was never reached. Failing right away lets the fallback handle it.
MAX_RETRIES = 0
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def ollama_client(settings: Mapping[str, str]) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "CF-Access-Client-Id": settings.get("CF_ACCESS_CLIENT_ID", ""),
            "CF-Access-Client-Secret": settings.get("CF_ACCESS_CLIENT_SECRET", ""),
            "User-Agent": "artefact-music-emporium",
        },
    )


def openrouter_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "artefact-music-emporium"})


def _ollama_model(settings: Mapping[str, str]) -> OpenAIChatModel:
    client = AsyncOpenAI(
        base_url=f"{settings['OLLAMA_BASE_URL'].rstrip('/')}/v1",
        api_key="ollama",
        http_client=ollama_client(settings),
        max_retries=MAX_RETRIES,
    )
    provider = OllamaProvider(openai_client=client)
    return OpenAIChatModel(settings["OLLAMA_CHAT_MODEL"], provider=provider)


def _openrouter_model(settings: Mapping[str, str]) -> OpenAIChatModel:
    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings["OPENROUTER_API_KEY"],
        http_client=openrouter_client(),
        max_retries=MAX_RETRIES,
    )
    provider = OpenRouterProvider(openai_client=client)
    return OpenAIChatModel(settings["OPENROUTER_CHAT_MODEL"], provider=provider)


def build_model(settings: Mapping[str, str]) -> tuple[Model, str]:
    """Returns the model to run and the primary's name, which tells a fallback reply apart."""
    models: list[Model] = []
    if settings.get("OLLAMA_BASE_URL") and settings.get("OLLAMA_CHAT_MODEL"):
        models.append(_ollama_model(settings))
    if settings.get("OPENROUTER_API_KEY") and settings.get("OPENROUTER_CHAT_MODEL"):
        models.append(_openrouter_model(settings))
    if not models:
        raise ValueError("no model provider configured")
    model = models[0] if len(models) == 1 else FallbackModel(*models)
    return model, models[0].model_name
