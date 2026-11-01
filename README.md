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
| `make policy-check` | Scores policy retrieval against 16 gold questions (needs an embedding provider) |
| `make policy-index` | Rebuilds `data/policies.sqlite` from the PDF, only needed if the PDF or model changes |

`make run`, `make run-dev` and `make test` run the setup themselves, so each one works on a fresh
checkout.

### Settings

The chat needs no settings to start. To change one, copy `.env.example` to `.env`.

| Setting | Values | Default | Effect |
|---|---|---|---|
| `EMPORIO_AGENT` | `stand_in` | `stand_in` | The agent to use |
| `EMPORIO_TROUBLESHOOTING` | `0` or `1` | `0` | Shows how each reply was produced |
| `EMPORIO_REPLY_TIMEOUT_SECONDS` | Positive number | `60` | How long to wait for a reply |

Settings are read once at startup, so restart the chat after changing one. An invalid value shows an
error page naming the setting.

### Stand-in agent

The real agent isn't built yet, so the chat uses a stand-in agent that needs no model or store data. The
page shows a notice that its replies are simulated. Start a message with one of these commands to
simulate a situation:

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

## Assumptions

The store manual contradicts itself on the WhatsApp number, the email address and the credit card
installment minimums. The rules the agent follows, and the questions still open with the store, are
in [Stakeholder Clarifications](docs/stakeholder-clarifications.md). Issues in the store data are in
[Store Data Corner Cases](docs/corner-cases/store-data.md).

## Decisions

- **Streamlit, called directly:** the chat calls the agent in the same process, with no API layer. This
  keeps the prototype to one command while the focus is on the agent and its evaluation. The agent
  doesn't depend on Streamlit, so it can be called from a script or test.
- **One small agent interface:** the chat only knows `respond(conversation_id, message)`. Reply details
  are plain dataclasses with a generic list of steps, so they don't tie the chat to an agent framework.
- **Stand-in agent:** it lets the chat and its failure paths be built and tested with no model or store
  data. It's never used silently: the page shows a notice, and a real agent that fails to start shows an
  error instead of falling back to it.
- **Plain text only:** messages and replies are rendered with `st.text`, so text from customers or tools
  can't change the page. This gives up lists and emphasis in replies, which can be revisited if the real
  agent needs them.
- **Secrets removed in one place:** replies and details pass through the sanitizer as soon as the agent
  returns, before anything is stored, so no view can skip it. With troubleshooting off, details are
  discarded and never stored.
- **Long messages:** they're validated after sending rather than with a character limit on the input.
  This tells the person what happened in Portuguese and never cuts their text silently.
- **Troubleshooting off by default:** it can only be turned on in the startup settings, never from the
  page.
- **Policy index committed to the repo:** `data/policies.sqlite` holds the manual split into its 28 numbered
  sections, with vectors and keyword search, so nobody needs an embedding provider to get it. Sections 7 and
  10 are instructions for staff, so customer searches skip them. It uses `qwen3-embedding:4b`, the smallest
  model available on both the local Ollama server and OpenRouter, and vectors from one work with questions
  embedded on the other. On 16 gold questions, the right section is in the top 3 for all 16 and first for 12,
  on both providers. Keyword search alone gets 15 of 16 in the top 3, and misses "Me arrependi da minha
  compra".
- **Setuptools as the build backend:** the `src/` layout needs a build system, or `import emporio` fails.
  Setuptools finds the package with no extra settings.

## Known Limitations

- **Interface:** the chat runs in one process and is meant for local use and small demos. There's no
  login, so it binds to localhost. A real integration would need a separate API.
- **Conversations aren't saved:** a conversation ends when the page is refreshed or closed.
- **Timed-out calls keep running:** a running call can't be interrupted, so a call that times out continues
  until it ends, and its result is discarded. The real agent should set timeouts on its own model and tool
  calls.
- **Secret removal only knows configured values:** it removes values from `.env` and sensitive
  environment variables, and anything under a sensitive key name. Another secret in free text, such as a
  third-party token in a tool's error message, isn't caught.
- **Message length:** there's no live character count, and an over-limit message is only rejected after
  sending. Streamlit's `max_chars` would add a live count, but it silently drops a paste over the limit, so
  the chat keeps the edit panel instead.
- **Troubleshooting view:** it shows customer data unmasked, because the data is fictional and the mode is
  for local use. Real customer data would require masking or restricted access.
- **Crash details:** `make run` hides application crash details from the browser, and `make run-dev`
  shows them in full to make debugging easier. Streamlit displays these details itself, so they skip
  the step that removes secrets. A secret in a crash message could appear on screen in `make run-dev`,
  so review any screenshot of a crash before sharing it.
