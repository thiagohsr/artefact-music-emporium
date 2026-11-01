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

## Known Limitations

> **Draft:** this describes planned behavior for the chat, which is not built yet.

- **Crash details:** `make run` hides application crash details from the browser, and `make run-dev`
  shows them in full to make debugging easier. Streamlit displays these details itself, so they skip
  the step that removes secrets. A secret in a crash message could appear on screen in `make run-dev`,
  so review any screenshot of a crash before sharing it.
