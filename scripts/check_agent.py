import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass

from emporio.agent.store.agent import create_store_agent

REPLY_LIMIT_SECONDS = 60


@dataclass(frozen=True)
class Check:
    name: str
    messages: Sequence[str]
    tools: Sequence[str] = ()
    answer: str = ""
    no_tools: bool = False


CHECKS = (
    Check("greeting", ("Oi, boa tarde!",), no_tools=True),
    Check("vague need", ("Queria uma ajuda",), no_tools=True),
    Check("brief: catalog", ("Quais opções de violões disponíveis custando até R$1000?",), ("search_products",), r"R\$"),
    Check("brief: store address", ("Qual o endereço da loja?",), ("policy_lookup",), r"14 de Maio"),
    Check("brief: price", ("Quanto custa o Takamine GD20?",), ("get_product",), r"2[.,]?199"),
    Check("price range", ("Uma guitarra a partir de 7000 reais até 15 mil reais",), ("search_products",), r"7[.,]?500|12[.,]?500"),
    Check("installments", ("Quanto fica o Takamine GD20 em 12x?",), ("payment_terms",), r"183,25"),
    Check("below minimum", ("Posso parcelar R$ 500 em 10 vezes?",), ("payment_terms",), r"100"),
    Check("promotion", ("Quanto custa o Crafter HT-100?",), ("get_product",), r"2[.,]?399[\s\S]*18\s?%|18\s?%[\s\S]*2[.,]?399"),
    Check("out of stock", ("Quero o violão Giannini GF-3D",), ("get_product",), r"indispon|esgot|sem estoque|fora de estoque"),
    Check("discontinued", ("Vocês têm o Shelby SN-7C?",), ("get_product",), r"descontinu|não faz mais parte|fora de linha|não .*catálogo"),
    Check("expired promotion", ("O Crafter CE-15 ainda está com 10% de desconto?",), ("get_product",), r"3[.,]?899"),
    Check("complaint", ("Quero reclamar: meu violão chegou riscado e ninguém me responde",), ("register_complaint",), r"24"),
    Check("accessories", ("Vocês vendem cordas de violão?",), (), r"instrumentos"),
    Check("closing", ("Qual o endereço da loja?", "Não, era só isso, obrigado!"), ("finish_conversation",)),
)


def run_check(agent, index: int, check: Check) -> bool:
    started = time.monotonic()
    called: list[str] = []
    answer = ""
    try:
        for message in check.messages:
            reply = agent.respond(f"check-{index}", message)
            answer = reply.answer
            called += [step.name for step in reply.details.steps if step.kind != "reasoning"]
    except Exception as error:  # noqa: BLE001 - a failure in one check must not hide the others
        print(f"FAIL {check.name}: {type(error).__name__}, {time.monotonic() - started:.1f}s")
        return False
    elapsed = time.monotonic() - started
    problems = [f"missing tool {tool}" for tool in check.tools if tool not in called]
    if check.no_tools and called:
        problems.append("called a tool")
    if "function_call" in answer or re.search(r"\b(finish_conversation|payment_terms|get_product)\b", answer):
        problems.append("a tool's name leaked into the answer")
    if check.answer and not re.search(check.answer, answer, re.IGNORECASE):
        problems.append(f"answer doesn't match {check.answer!r}")
    if elapsed > REPLY_LIMIT_SECONDS * len(check.messages):
        problems.append("over the reply limit")
    label = "FAIL" if problems else "PASS"
    print(f"{label} {check.name}: {elapsed:.1f}s, tools={called}{', ' + '; '.join(problems) if problems else ''}")
    if problems:
        print(f"     answer: {answer[:300]!r}")
    return not problems


def main() -> None:
    agent = create_store_agent(REPLY_LIMIT_SECONDS)
    results = [run_check(agent, index, check) for index, check in enumerate(CHECKS)]
    print(f"\n{sum(results)} of {len(results)} checks passed")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
