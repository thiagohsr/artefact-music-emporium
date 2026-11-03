# Quickstart: Validate the Agent

## Prerequisites

uv, `OPENROUTER_API_KEY` and `OPENROUTER_CHAT_MODEL` in `.env`, or access to the self-hosted server.

## Automated checks

```bash
make test
make policy-check
make agent-check
```

`make test` uses no network. `make agent-check` covers SC-001 on the real model, reporting each question, the tools
called and whether the expected values appeared.

## In the chat

```bash
make run-dev
```

Expand "Reply details" to see tools and sources. Order details come from `data/emporio.sqlite`.

| # | Do this | Expected | Covers |
|---|---|---|---|
| 1 | Say "Oi" | A greeting, asking how it can help, with no tool in the details | US1 |
| 2 | Ask something vague, like "Queria uma ajuda" | It asks what you need | US1 |
| 3 | Ask "Quanto custa o Takamine GD20?" | R$ 2.199,00, from `get_product`, then asks if you need anything else | US1 |
| 3a | Ask "Uma guitarra a partir de 7000 reais até 15 mil reais" | Only guitars in that range, from `search_products` with both limits | US1 |
| 4 | Ask "Quanto fica em 12x?" | The installment from `payment_terms`, using the earlier product | US1, US3 |
| 5 | Ask about R$ 500 in 10x | Not allowed, because it's below the R$ 100 minimum | US1 |
| 6 | Ask for the Giannini GF-3D | Temporarily unavailable, with in-stock alternatives | US1 |
| 7 | Ask for the Shelby SN-7C | No longer in the catalog, with equivalents | US1 |
| 8 | Ask to buy strings | The store only sells instruments | US1 |
| 9 | Make a complaint | Empathy, `register_complaint`, 24 business hours | US1 |
| 10 | Ask about an order with no phone or email | It asks for both and shares nothing | US2 |
| 11 | Try a wrong phone, then a wrong email, then a made-up order | The same reply each time | US2 |
| 12 | Give the correct tracking code, phone and email | The order's details | US2 |
| 13 | Reload, verify again | The conversation continues through `find_open_conversation` | US3 |
| 14 | Click "Nova conversa", then cancel | Nothing changes | US3 |
| 15 | Click "Nova conversa", confirm, verify again | A new conversation, with nothing continued | US3 |
| 16 | Say you need nothing else | A polite close, with `finish_conversation` in the details | US1 |
| 17 | Check the stored data | `sqlite3 data/emporio.sqlite "SELECT messages FROM stored_conversations;"` shows no readable name, phone or email | SC-004 |

## Failures

| # | Do this | Expected | Covers |
|---|---|---|---|
| 18 | Set an unreachable `OLLAMA_BASE_URL` | The fallback answers, and the details show it | US4 |
| 19 | Remove every provider | An error page naming `EMPORIO_AGENT`, and the cause in the terminal | US4 |
| 20 | Press Streamlit's Stop during a wait | Record what happens, and fix it if the page is stuck | FR-021 |
