<sub>DESAFIO TÉCNICO · AI ENGINEER</sub>

# Empório da Música — Customer Service Agent

**Thiago Ramos — AI Engineer**

Repository: [github.com/thiagohsr/artefact-music-emporium](https://github.com/thiagohsr/artefact-music-emporium)<br>
Live demo: [artefact-music-emporium.streamlit.app](https://artefact-music-emporium.streamlit.app/) · runs on Streamlit's
free tier, so if it's asleep, give it a minute to tune its strings 🎸

## What I built

A Python text-message agent that serves the customers of Empório da Música, a fictional instrument store, in Brazilian
Portuguese:

- **Persona:** the store's own tone and service rules, loaded from section 7 of its manual, in short WhatsApp-style
  replies.
- **Grounded answers:** prices, stock and orders come from the store data, and rules from the policy manual, never from
  the model's memory.
- **Data or policy:** eight typed tools. Catalog, prices, installments and orders query the data; returns, hours and
  payment rules search the manual.
- **Out of scope:** a closed scope with a one-sentence, friendly decline, including attempts to override the
  instructions.

## Tech decisions

| Decision | Choice | Why |
|---|---|---|
| **Agent approach** | Pydantic AI, one agent with function calling over typed tools, plus RAG over the manual | Choosing the source is the core task, and a tool loop recovers from a wrong first call. A router only if evals demand it |
| **Model and provider** | `qwen3:8b` on self-hosted Ollama, with `gpt-4o-mini` on OpenRouter as fallback | Runs on a 16 GB GPU; OpenRouter lets anyone run it without the server |
| **Retrieval** | The manual split into its 28 sections, vector search with `qwen3-embedding:4b` and keyword fallback | The right section is in the top 3 for 16 of 16 test questions |
| **Prompt strategy** | Manual section 7 as written, inside labelled sections, with example declines | The store's voice drives the agent; the closed scope stops generic-assistant answers |
| **Interface** | Streamlit chat, with a troubleshooting view of tools and sources | One command to run; time goes to the agent and its evaluation |
| **Conversation history** | Kept per session and through a page reload; verified customers' conversations stored masked | Follow-ups work, and a reload doesn't lose a quote |
| **Data treatment** | CSVs loaded into SQLite; the manual's contradictions resolved and documented | Exact values computed in code, assumptions on record |

> **Exact things live in code:** prices, installments, return windows and the identity check (tracking code, phone and
> email) are computed by the tools, so the model only reads results.

[DECISIONS.md](DECISIONS.md) has the reasoning, alternatives and evidence behind each choice, and the assumptions are in
[docs/stakeholder-clarifications.md](docs/stakeholder-clarifications.md).

## Getting started

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and `make`. Copy `.env.example` to `.env` and
connect a model, then run `make run` and open <http://localhost:8501>.

| Command | What it does |
|---|---|
| `make run` | Starts the chat, installing everything it needs first |
| `make run-dev` | Starts the chat with the troubleshooting view: tools, sources and model for each reply |
| `make test` | Runs the automated tests, with no model needed |
| `make agent-check` | Asks the acceptance questions on the real model |
| `make evals` | Scores the return cases five times each on the real model |
| `make policy-check` | Scores the policy search on 16 gold questions |
| `make policy-index` | Rebuilds the policy index, only needed if the PDF or embedding model changes |

### Connecting a model

With both configured, the self-hosted Ollama server is tried first and OpenRouter is the fallback.

| Option | Set in `.env` | Notes |
|---|---|---|
| **OpenRouter** (quickest) | `OPENROUTER_API_KEY` | Create a key at [openrouter.ai](https://openrouter.ai/keys) |
| **Your own Ollama** | `OLLAMA_BASE_URL`, such as `http://localhost:11434` | Run `ollama pull qwen3:8b && ollama pull qwen3-embedding:4b` first. Both took about 12 GB of GPU memory at a 16k context; raise Ollama's 4k default with `OLLAMA_CONTEXT_LENGTH` |
| **The project's server** | `OLLAMA_BASE_URL`, `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` | Not published: ask for them by replying to the selection process e-mail |

- **Models:** `.env.example` lists the chat and embedding model settings with their defaults. Chat models can change
  freely; after changing an embedding model, run `make policy-index`.
- **One provider only:** leave the other one empty on the command line, which overrides `.env`, for example
  `OLLAMA_BASE_URL= make run` for OpenRouter only.
- **Other settings:** `EMPORIO_TROUBLESHOOTING` (`0` or `1`) and `EMPORIO_REPLY_TIMEOUT_SECONDS` (default `60`). They're
  read once at startup, and an invalid value shows an error page naming it.

### Stand-in agent

`EMPORIO_AGENT=stand_in make run-dev` uses a simulated agent that needs no model or store data, to test the chat itself.
Start a message with a command to simulate a situation: `/ferramenta` (tool call), `/politica` (policy lookup),
`/fallback`, `/raciocinio` (reasoning), `/grande` (large details), `/incompleto`, `/sem-detalhes`, `/sensivel` (a fake
API key that must never show), `/erro` (agent failure) or `/lento` (slower than the time limit).

## Example conversations

Five real conversations with the agent, in [data/example-conversation](data/example-conversation): the brief's four
suggestions plus an out-of-scope request. Each shows the conversation first, then a collapsed section with the tools,
results, reasoning, time and tokens.

| Brief's suggestion | What it shows | Conversation |
|---|---|---|
| "Quais opções de violões disponíveis custando até R$1000?" | Catalog search with a price limit | [busca-no-catalogo.md](data/example-conversation/busca-no-catalogo.md) |
| "Qual o endereço da loja?" | Store information from the manual | [informacoes-da-loja.md](data/example-conversation/informacoes-da-loja.md) |
| "Quanto custa o Takamine GD20?" | A price, then installments in a follow-up | [preco-e-parcelamento.md](data/example-conversation/preco-e-parcelamento.md) |
| "Me arrependi da minha compra, posso devolver meu pedido?" | **Non-trivial:** verifies the customer by tracking code, phone and email, then applies the return policy to the order | [devolucao-com-pedido.md](data/example-conversation/devolucao-com-pedido.md) |
| A recipe request | Declining a request outside the store's scope | [fora-do-escopo.md](data/example-conversation/fora-do-escopo.md) |

To try the return yourself, use the tracking code `BRKR1122334BR`, phone `(67) 99789-0123` and e-mail
`leticia.rocha@jmail.com` from the store data.

## Known limitations and next steps

### Limitations

- **Results vary between runs:** neither model reliably checks the return policy before answering a return, and
  `gpt-4o-mini` once denied a return that was still allowed.
- **Orders without a tracking code yet can't be looked up:** the code is sent on dispatch, so pending, confirmed and
  cancelled orders get pointed to the store's channels.
- **One process, no login:** meant for local use and demos. Stored conversations aren't deleted on request yet.

[DECISIONS.md](DECISIONS.md#known-limitations) lists the rest.

### With more time

- **Return rules delivered by the order tool itself,** so the model doesn't have to remember to look them up.
- **A larger eval suite:** retrieval questions, off-topic and attack cases, a tone judge, and a comparison of newer or
  larger models on the same cases.
- **Recovery by phone and email** for a closed tab or another device, already designed in
  [spec 003](specs/003-conversation-recovery/spec.md).
- **Production pieces:** a separate API, Postgres, prompt caching and stronger protection of stored data.

## AI coding assistant usage

I used Claude Code in VS Code, mostly Sonnet 5.5 and Opus 5.5 at medium effort, and Fable 5.1 for some of the reasoning.

My workflow was agentic development driven by Spec Kit: each feature went through a specification, a plan and a task
list before any code, and the code was mostly written test-first. The specifications live alongside the code, and
[.specify/memory/constitution.md](.specify/memory/constitution.md) gives the project's principles.

- **Tests that don't need a model:** 451 tests cover 98% of the source code.
- **Measured retrieval:** 16 of 16 gold questions find the right manual section in the top 3.
- **Measured behavior:** repeated runs on the real models, which is how weaknesses were found rather than guessed.
- **Human in the loop:** I confirmed the scope of every specification, corrected the assistant with evidence, and tested
  the real app myself, which caught issues the tests missed.

That is why small, low-cost models are enough: what must be exact lives in tested code, and the evals show where the
models still fall short.
