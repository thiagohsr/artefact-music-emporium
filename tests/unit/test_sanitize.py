import pytest

from emporio.agent.contract import AgentReply, ReplyDetails, Step
from emporio.safety.sanitize import REDACTED, Sanitizer, load_private_values

PRIVATE_VALUE = "planted-private-value"


@pytest.fixture
def sanitizer():
    return Sanitizer([PRIVATE_VALUE])


def test_private_values_are_removed_from_text(sanitizer):
    cleaned = sanitizer.text(f"antes {PRIVATE_VALUE} depois")

    assert cleaned == f"antes {REDACTED} depois"


def test_nested_values_and_dictionary_keys_are_sanitized(sanitizer):
    cleaned = sanitizer.clean(
        {
            f"chave-{PRIVATE_VALUE}": [{"detalhe": f"usando {PRIVATE_VALUE}"}, (PRIVATE_VALUE,)],
            "numero": 3,
            "ativo": True,
            "nada": None,
        }
    )

    assert PRIVATE_VALUE not in str(cleaned)
    assert cleaned["numero"] == 3
    assert cleaned["ativo"] is True
    assert cleaned["nada"] is None


def test_values_under_sensitive_keys_are_removed(sanitizer):
    cleaned = sanitizer.clean({"api_key": "short", "total_tokens": 42})

    assert cleaned == {"api_key": REDACTED, "total_tokens": 42}


def test_objects_that_are_not_json_become_sanitized_text(sanitizer):
    class Custom:
        def __str__(self):
            return f"objeto com {PRIVATE_VALUE}"

    assert PRIVATE_VALUE not in sanitizer.clean(Custom())


def test_exception_text_is_sanitized(sanitizer):
    assert PRIVATE_VALUE not in sanitizer.text(str(ValueError(f"falhou com {PRIVATE_VALUE}")))


def test_reply_dataclasses_are_sanitized_and_keep_their_types(sanitizer):
    reply = AgentReply(
        answer=f"resposta {PRIVATE_VALUE}",
        details=ReplyDetails(
            steps=(Step(name="passo", kind="tool", result={"r": PRIVATE_VALUE}, error=f"erro {PRIVATE_VALUE}", duration_ms=5),),
            errors=(f"erro {PRIVATE_VALUE}",),
            model="qwen3:8b",
        ),
    )

    cleaned = sanitizer.clean(reply)

    assert isinstance(cleaned, AgentReply)
    assert isinstance(cleaned.details.steps[0], Step)
    assert cleaned.details.steps[0].duration_ms == 5
    assert cleaned.details.model == "qwen3:8b"
    assert PRIVATE_VALUE not in str(cleaned)


def test_ordinary_text_is_kept(sanitizer):
    text = "O violão custa R$ 1.200,00 e o pedido 123 foi enviado. Token de agradecimento!"

    assert sanitizer.text(text) == text


def test_longer_private_values_are_removed_first():
    sanitizer = Sanitizer(["segredo-curto", "segredo-curto-e-mais-longo"])

    assert sanitizer.text("segredo-curto-e-mais-longo") == REDACTED


def test_private_values_come_from_env_file_and_sensitive_variables(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CUSTOM_VALUE=from-the-env-file\n"
        "OPENROUTER_MODEL=openai/gpt-4o-mini\n"
        "EMPORIO_AGENT=stand_in\n"
        "TINY=abc\n"
        "EMPTY=\n"
    )
    environ = {
        "MY_API_KEY": "from-sensitive",
        "HOME_REGION": "not-sensitive-value",
        "OLLAMA_MODEL": "qwen3:8b-model-name",
    }

    values = load_private_values(environ=environ, env_file=env_file)

    assert set(values) == {"from-the-env-file", "from-sensitive"}


def test_missing_env_file_is_allowed(tmp_path):
    assert load_private_values(environ={}, env_file=tmp_path / "missing") == []


@pytest.mark.parametrize("value", [["abcdefghijkl1234"], ("a", "b"), 12345678901, 3.14, {"nested": "x"}])
def test_any_value_under_a_sensitive_name_is_removed(sanitizer, value):
    assert sanitizer.clean({"api_key": value}) == {"api_key": REDACTED}


@pytest.mark.parametrize("name", ["token", "access_token", "ACCESS_TOKEN", "auth_token", "password", "client_secret"])
def test_sensitive_names_still_match(sanitizer, name):
    assert sanitizer.clean({name: "x"}) == {name: REDACTED}


@pytest.mark.parametrize("name", ["total_tokens", "input_tokens", "tokens"])
def test_token_counts_are_kept(sanitizer, name):
    assert sanitizer.clean({name: 42}) == {name: 42}


@pytest.mark.parametrize("value", [None, ""])
def test_empty_values_under_sensitive_names_stay_empty(sanitizer, value):
    assert sanitizer.clean({"api_key": value}) == {"api_key": value}


def test_exception_text_and_traceback_are_sanitized(sanitizer):
    try:
        raise ValueError(f"falhou com {PRIVATE_VALUE}")
    except ValueError as error:
        described = sanitizer.exception(error)

    assert "Traceback" in described
    assert "ValueError" in described
    assert PRIVATE_VALUE not in described

