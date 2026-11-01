import contextlib
import sqlite3
import sys

from emporio.data.policy_index import (
    INDEX_PATH,
    embed_with_ollama,
    embed_with_openrouter,
    is_compatible,
    ollama_embedding_model,
    openrouter_embedding_model,
    read_settings,
    search_keywords,
    search_vectors,
)

MIN_TOP3_RECALL = 0.8

GOLD_SET = (
    ("Me arrependi da minha compra, posso devolver meu pedido?", {"4.1"}),
    ("Qual o endereço da loja?", {"1.2"}),
    ("Vocês abrem no sábado?", {"2"}),
    ("Quais são as formas de pagamento?", {"3"}),
    ("Posso parcelar em 10 vezes? Qual o valor mínimo da parcela?", {"3.1"}),
    ("Meu violão veio com defeito, posso trocar?", {"4.2", "8.1"}),
    ("Não gostei da cor do instrumento, consigo trocar por outro?", {"4.3"}),
    ("Quais produtos não podem ser trocados?", {"4.4"}),
    ("Quanto tempo demora a entrega aqui em Campo Grande?", {"5.1"}),
    ("Vocês entregam para São Paulo? Como funciona o frete?", {"5.2"}),
    ("Como faço para rastrear meu pedido?", {"5.3"}),
    ("Vocês fazem promoção na Black Friday?", {"6.1"}),
    ("Posso juntar uma promoção com o desconto do PIX?", {"6.2"}),
    ("Quanto tempo de garantia tem um instrumento?", {"8.1", "8.2"}),
    ("A garantia cobre se eu deixar o instrumento cair?", {"8.3"}),
    ("Como peço para apagar meus dados pessoais?", {"9"}),
)


def report(name: str, results: list[tuple[str, set[str], list[str]]]) -> float:
    top1 = sum(found[:1] != [] and found[0] in expected for _, expected, found in results)
    top3 = sum(bool(expected & set(found[:3])) for _, expected, found in results)
    print(f"\n{name}: top-1 {top1}/{len(results)}, top-3 {top3}/{len(results)}")
    for question, expected, found in results:
        if not found or found[0] not in expected:
            print(f"  expected {sorted(expected)}, got {found}: {question}")
    return top3 / len(results)


def main() -> None:
    settings = read_settings()
    questions = [question for question, _ in GOLD_SET]
    embedders = {}
    if settings.get("OLLAMA_BASE_URL"):
        embedders["ollama"] = (embed_with_ollama, ollama_embedding_model(settings))
    if settings.get("OPENROUTER_API_KEY"):
        embedders["openrouter"] = (embed_with_openrouter, openrouter_embedding_model(settings))

    with contextlib.closing(sqlite3.connect(f"file:{INDEX_PATH}?mode=ro", uri=True)) as conn:
        recalls = []
        for provider, (embed, model) in embedders.items():
            if not is_compatible(conn, model):
                sys.exit(f"{model} did not build this index. Run: make policy-index")
            vectors = embed(questions, settings)
            recalls.append(
                report(
                    f"vectors, questions embedded on {provider}",
                    [
                        (question, expected, [match.number for match in search_vectors(conn, vector)])
                        for (question, expected), vector in zip(GOLD_SET, vectors, strict=True)
                    ],
                )
            )
        recalls.append(
            report(
                "keywords (FTS5), no provider needed",
                [
                    (question, expected, [match.number for match in search_keywords(conn, question)])
                    for question, expected in GOLD_SET
                ],
            )
        )

    if min(recalls) < MIN_TOP3_RECALL:
        sys.exit(f"\nTop-3 recall is below {MIN_TOP3_RECALL:.0%} on at least one path.")


if __name__ == "__main__":
    main()
