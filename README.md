# Empório da Música Service Agent

Text-message customer service agent prototype for Empório da Música, a fictional musical instrument
store.

## Getting Started

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and `make`.

| Command | What it does |
|---|---|
| `make setup` | Creates the virtualenv and installs the locked dependencies |
| `make run` | Starts the chat at <http://localhost:8501> |
| `make run-dev` | Starts the chat with the troubleshooting view and crash details on |
| `make test` | Runs the automated tests |
| `make agent-check` | Asks the acceptance questions on the real model, and needs a provider |
| `make evals` | Scores the return cases five times each on the real model, and needs a provider |
| `make policy-check` | Scores policy retrieval against 16 gold questions (needs an embedding provider) |
| `make policy-index` | Rebuilds `data/policies.sqlite` from the PDF, only needed if the PDF or model changes |

`make run`, `make run-dev` and `make test` run the setup themselves, and the two chat commands also prepare the store
database.

### Settings

Copy `.env.example` to `.env`. The agent needs a model provider, and the quickest is OpenRouter: set
`OPENROUTER_API_KEY` and leave the rest as they are. Without a provider, the page shows an error naming `EMPORIO_AGENT`.

| Setting | Values | Default | Effect |
|---|---|---|---|
| `EMPORIO_AGENT` | `store` or `stand_in` | `store` | The agent to use |
| `EMPORIO_TROUBLESHOOTING` | `0` or `1` | `0` | Shows how each reply was produced |
| `EMPORIO_REPLY_TIMEOUT_SECONDS` | Positive number | `60` | How long to wait for a reply |

Settings are read once at startup, so restart the chat after changing one. An invalid value shows an
error page naming the setting.

### Connecting a real model

The agent needs at least one model provider. With both configured, the self-hosted Ollama server is tried first and
OpenRouter is the fallback.

| Option | Set in `.env` | Notes |
|---|---|---|
| **OpenRouter** (quickest) | `OPENROUTER_API_KEY` | Create a key at [openrouter.ai](https://openrouter.ai/keys). Uses `openai/gpt-4o-mini` for chat and `qwen/qwen3-embedding-4b` for the policy search |
| **Your own Ollama** | `OLLAMA_BASE_URL`, such as `http://localhost:11434` | Pull the models first: `ollama pull qwen3:8b && ollama pull qwen3-embedding:4b`. Both together took about 12 GB of GPU memory at a 16k context. Ollama defaults to a 4k context on GPUs under 24 GB, so raise it with `OLLAMA_CONTEXT_LENGTH` |
| **The project's own server** | `OLLAMA_BASE_URL`, `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` | Not published: ask for them by replying to the selection process e-mail |

| Setting | Default | Effect |
|---|---|---|
| `OLLAMA_CHAT_MODEL` | `qwen3:8b` | Chat model on Ollama |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:4b` | Embedding model on Ollama |
| `OPENROUTER_CHAT_MODEL` | `openai/gpt-4o-mini` | Chat model on OpenRouter |
| `OPENROUTER_EMBEDDING_MODEL` | `qwen/qwen3-embedding-4b` | Embedding model on OpenRouter |

- **Chat models** can change freely. The committed policy index only works with the embedding model that built it, so
  run `make policy-index` after changing an embedding model.
- **To use only one provider** for a run, leave the other one empty on the command line, which overrides `.env`:
  `OLLAMA_BASE_URL= make run` for OpenRouter only, or `OPENROUTER_API_KEY= make run` for Ollama only.
- **To see which model answered**, start with `make run-dev`: each reply shows the model, the provider and whether the
  fallback was used.

### Stand-in agent

`EMPORIO_AGENT=stand_in make run-dev` uses a simulated agent that needs no model or store data, and the page says its replies
are simulated. Start a message with one of these commands to simulate a situation:

| Command | Simulates |
|---|---|
| `/ferramenta` | A tool call and a store data source |
| `/politica` | A policy lookup and a policy source |
| `/fallback` | A reply from a fallback provider |
| `/raciocinio` | A reasoning step |
| `/grande` | Details large enough to open the modal |
| `/incompleto` | Incomplete details |
| `/sem-detalhes` | No details at all |
| `/sensivel` | A fake API key, which must never appear on the page |
| `/erro` | The agent failing during a reply |
| `/lento` | A reply slower than the time limit |

## Technical Decisions

The main choices, in one line each. [DECISIONS.md](DECISIONS.md) has the reasoning, the alternatives and the
evidence behind them.

| Decision | Choice | Why |
|---|---|---|
| **Agent approach** | One Pydantic AI agent with a tool loop over eight typed tools | Choosing the right source is the core of the brief, and in a loop a wrong first call is cheap. A router with specialist agents is the next step only if evaluation shows wrong tool choices |
| **LLM and provider** | `qwen3:8b` on a self-hosted Ollama server, with thinking on, and `gpt-4o-mini` on OpenRouter as the fallback | Runs on a 16 GB GPU, while OpenRouter is what an evaluator without the server uses. Turning thinking off made one reply state a made-up price |
| **What must be exact lives in code** | Prices, stock, installments, return windows and the identity check are computed by the tools | Small models get dates and arithmetic wrong, so they only read the results |
| **Retrieval** | The manual split into its 28 sections, searched by vectors (`qwen3-embedding:4b`) with keyword search as a fallback, in an index committed to the repo | The right section is in the top 3 for 16 of 16 test questions, and nobody needs an embedding provider to get the index |
| **Prompt strategy** | Section 7 of the manual loaded as written, inside labelled sections for identity, scope, answer style, sources and orders, with example declines | The store's own tone and rules drive the agent, and the closed scope stops general-assistant answers |
| **Conversation history** | Kept for the session, and through a page reload via a link in the address, for 30 minutes. Verified customers' conversations are also stored masked, under a random user ID | Follow-ups work, and an accidental reload doesn't lose a quote |
| **Customer privacy** | Order details only with the tracking code, phone and email together, checked in the tool | Order IDs are sequential and easy to guess, and the model never decides who someone is |
| **Interface** | Streamlit, calling the agent in the same process | One command to run, with the time spent on the agent and its evaluation |

## Known Limitations

The main ones are below, and [DECISIONS.md](DECISIONS.md#known-limitations) lists them all.

- **Reliability varies between runs.** `make evals` shows that neither model reliably checks the return policy before
  answering a return, and `gpt-4o-mini` denied a return that was still allowed in 3 of 5 runs.
- **Orders without a tracking code can't be looked up.** The code is sent when an order is dispatched, so pending,
  confirmed and cancelled orders, 12 of the 20 in the data, get pointed to the store's channels.
- **Links and images in replies render** because replies use Markdown, and nothing filters them yet.
- **One process, no login, no deletion on request.** The chat is meant for local use and demos, and stored conversations
  aren't deleted when a customer asks, which manual section 9 allows.

## What I Would Do With More Time

- **Fix the return answers in code:** put the relevant manual sections and the open or closed windows, in plain words,
  into the order result, so the model doesn't have to remember to look them up.
- **Grow the evaluation suite:** move the older `make agent-check` questions into `make evals`, add off-topic and attack
  cases, a judge for tone, cases kept out of prompt tuning, and a comparison with a newer or larger Qwen on the same cases.
- **Recover a conversation from a phone and email,** for a closed tab or another device. It's designed in
  [spec 003](specs/003-conversation-recovery/spec.md) and not built, because the page link fixed the accidental reload
  with much less risk.
- **Protect stored data better:** a secret-keyed hash for the user ID instead of a mapping table, deletion on request,
  and filtering images out of replies.
- **Cache what's safe to cache:** the static start of the prompt, and question embeddings for the policy search, but
  never answers with prices, stock or orders.
- **Production pieces:** a separate API in front of the agent, Postgres instead of SQLite, and test fixtures that don't
  depend on the store's CSV rows.

## AI Coding Assistant Usage

I used the Claude Code extension in VS Code, mostly with the Sonnet 5.5 and Opus 5.5 models at medium effort, and
Fable 5.1 for some of the reasoning.

My workflow focused on agentic development through Spec Kit specifications, aiming to deliver most features with
quality despite the low-cost models the agent runs on: `qwen3:8b` locally and `gpt-4o-mini` on OpenRouter. It feels
like a way to deliver features through documentation that lives alongside the code. That makes it easier for anyone
who wants to improve a feature to meet its BDD specifications, or to get a quick overview of the project's purpose
through [.specify/memory/constitution.md](.specify/memory/constitution.md).

How I kept control of the work:

- **Scope before writing:** every specification started with me confirming its scope, and I removed features I hadn't
  asked for.
- **Correcting with evidence:** I pointed the agent's tone to section 7 of the manual, showed that a live character count
  was possible after being told it wasn't, and required that orders be found by tracking code only.
- **Testing it myself:** running the real app found what the tests missed, such as the fallback never being reached
  with my server off, a reload losing a quote, and a masking bug that broke saving on the hosted app.
- **Rules for the assistant:** one commit per subject, a secret scan before every commit, no force-pushes and no
  attribution lines.

## Example Conversations

The challenge brief suggests four scenarios. Each one has a real conversation with the agent in
[data/example-conversation](data/example-conversation), with a fifth for a request outside the store's scope. Every file
shows the conversation first, then a collapsed section with the tools called, their results, the model's reasoning, and
the time and tokens of each step.

| Brief's suggestion | What it shows | Conversation |
|---|---|---|
| "Quais opções de violões disponíveis custando até R$1000?" | Catalog search with a price limit | [busca-no-catalogo.md](data/example-conversation/busca-no-catalogo.md) |
| "Qual o endereço da loja?" | General store information, from the policy manual | [informacoes-da-loja.md](data/example-conversation/informacoes-da-loja.md) |
| "Quanto custa o Takamine GD20?" | A product's price, then installments in a follow-up | [preco-e-parcelamento.md](data/example-conversation/preco-e-parcelamento.md) |
| "Me arrependi da minha compra, posso devolver meu pedido?" | **Non-trivial:** verifies the customer by tracking code, phone and email, reads the order and applies the return policy | [devolucao-com-pedido.md](data/example-conversation/devolucao-com-pedido.md) |
| A recipe request | Declining a request outside the store's scope | [fora-do-escopo.md](data/example-conversation/fora-do-escopo.md) |

To try them yourself, start the chat with `make run-dev`. The return scenario needs an order's tracking code, phone
and email from the store data, for example `BRKR1122334BR`, `(67) 99789-0123` and `leticia.rocha@jmail.com`.
