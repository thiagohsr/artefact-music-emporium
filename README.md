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

## Technical Decisions and Limitations

[Technical Decisions and Limitations](DECISIONS.md) justifies the framework, model, retrieval
architecture, prompt strategy and conversation history, records the assumptions made where the store's
material is ambiguous, and lists the known limitations.

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
