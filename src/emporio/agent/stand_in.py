import time

from emporio.agent.contract import AgentReply, ReplyDetails, Source, Step

# Assembled from parts so that secret scanners do not flag a value that was never real.
FAKE_API_KEY = "sk-" + "standin" + "-not-a-real-key-000000"

MODEL = "stand-in"
PROVIDER = "simulated"
SIMPLE_ANSWER = "Olá! Esta é uma resposta simulada. Em que posso ajudar?"


def _details(**fields) -> ReplyDetails:
    return ReplyDetails(model=MODEL, provider=PROVIDER, **fields)


def _simple(_message: str) -> AgentReply:
    return AgentReply(SIMPLE_ANSWER, _details())


def _tool(_message: str) -> AgentReply:
    step = Step(
        name="buscar_produto",
        kind="tool",
        duration_ms=120,
        inputs={"produto": "violão"},
        result={"produto": "Violão simulado", "estoque": 3},
    )
    return AgentReply(
        "Temos 3 unidades do Violão simulado.",
        _details(steps=(step,), sources=(Source("data", "products"),)),
    )


def _policy(_message: str) -> AgentReply:
    step = Step(
        name="buscar_politica",
        kind="retrieval",
        duration_ms=80,
        inputs={"pergunta": "prazo de troca"},
        result="Trecho simulado do manual sobre trocas.",
    )
    return AgentReply(
        "De acordo com o trecho simulado do manual, você pode solicitar a troca.",
        _details(steps=(step,), sources=(Source("policy", "Seção simulada"),)),
    )


def _fallback(_message: str) -> AgentReply:
    return AgentReply("Esta resposta simulada veio do provedor reserva.", _details(fallback_used=True))


def _reasoning(_message: str) -> AgentReply:
    step = Step(
        name="raciocinio",
        kind="reasoning",
        duration_ms=40,
        result="A pergunta não precisa de consulta, então respondo diretamente.",
    )
    return AgentReply("Depois de pensar um pouco, aqui está a resposta simulada.", _details(steps=(step,)))


def _large(_message: str) -> AgentReply:
    steps = tuple(
        Step(
            name=f"etapa_{number}",
            kind="tool",
            duration_ms=10,
            inputs={"etapa": number},
            result="Resultado simulado. " * 150 if number == 1 else f"Resultado simulado {number}.",
        )
        for number in range(1, 13)
    )
    return AgentReply("Esta resposta simulada teve muitas etapas.", _details(steps=steps))


def _incomplete(_message: str) -> AgentReply:
    step = Step(name="buscar_produto", kind="tool", duration_ms=120)
    return AgentReply("Esta resposta simulada tem detalhes parciais.", _details(steps=(step,), complete=False))


def _no_details(_message: str) -> AgentReply:
    return AgentReply("Esta resposta simulada não tem detalhes.")


def _sensitive(_message: str) -> AgentReply:
    step = Step(
        name="chamar_servico",
        kind="tool",
        status="error",
        duration_ms=30,
        inputs={"servico": "simulado"},
        result={"resposta": f"chave usada: {FAKE_API_KEY}"},
        error=f"Falha simulada com a chave {FAKE_API_KEY}",
    )
    return AgentReply("Esta resposta simulada passou por um serviço sensível.", _details(steps=(step,)))


def _error(_message: str) -> AgentReply:
    raise RuntimeError("Falha simulada do agente")


class StandInAgent:
    name = "stand_in"
    is_simulated = True
    private_values = (FAKE_API_KEY,)

    def __init__(self, slow_seconds: float = 65) -> None:
        self._slow_seconds = slow_seconds
        self._commands = {
            "/ferramenta": _tool,
            "/politica": _policy,
            "/fallback": _fallback,
            "/raciocinio": _reasoning,
            "/grande": _large,
            "/incompleto": _incomplete,
            "/sem-detalhes": _no_details,
            "/sensivel": _sensitive,
            "/erro": _error,
            "/lento": self._slow,
        }

    def respond(self, conversation_id: str, message: str) -> AgentReply:
        words = message.split(maxsplit=1)
        command = words[0] if words else ""
        return self._commands.get(command, _simple)(message)

    def end_conversation(self, conversation_id: str) -> None:
        pass

    def _slow(self, message: str) -> AgentReply:
        time.sleep(self._slow_seconds)
        return _simple(message)
