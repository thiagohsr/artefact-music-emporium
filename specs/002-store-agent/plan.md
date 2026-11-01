# Implementation Plan: Store Customer Service Agent

**Branch**: `feature/002-store-agent` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-store-agent/spec.md`

## Summary

Replace the stand-in with one Pydantic AI agent that runs a plain tool loop over eight typed tools. Tools hold
everything that must be exact: lookups, payment calculations, the identity check and writes. Sections 7.1 to 7.3
of the manual become the agent's instructions. `qwen3:8b` answers first, with OpenRouter as the fallback.
Conversations live in memory for the session, and identified customers' conversations are also stored with their
personal data masked, so they can be continued after a page reload.

## Technical Context

**Language/Version**: Python 3.13, managed with uv

**Primary Dependencies**: Adds `pydantic-ai-slim[openai]>=2.64,<3` and `httpx>=0.28,<1`. Existing: Streamlit, python-dotenv.

**Storage**: `data/emporio.sqlite` gains conversation and complaint tables. `data/policies.sqlite` stays read-only.

**Testing**: pytest with Pydantic AI's test models and no network for `make test`. `make agent-check` runs SC-001
on the real model.

**Target Platform**: Local run on macOS and Linux.

**Project Type**: Single-process web application with a src-layout package.

**Performance Goals**: Replies within the existing 60-second limit. Measured on `qwen3:8b`: 3 to 14 s for up to two
tool calls, with eight tools still to be measured.

**Constraints**: Customer identity never comes from the model. No readable names, phones or emails in stored
conversations. `emporio.agent` must not import Streamlit.

**Scale/Scope**: One process and a few simultaneous sessions. Four simultaneous replies took 12.1 s in testing.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle or rule | How this feature complies | Status |
|---|---|---|
| I. Grounded Answers | Prices, stock and orders come from tools. Rules come from `policy_lookup`. Calculations are in `payment_terms`. Conflicts follow `docs/stakeholder-clarifications.md` | Pass |
| II. Right Source | The model picks tools, and each reply records them with a `data` or `policy` source | Pass |
| III. Customer Privacy | `get_order_status` requires the order number, phone and email, and returns the same reply for every failure. Identity is held by the session, not the model. Stored data is masked | Pass |
| IV. Persona and Scope | Section 7 sets the tone, flow and special situations. Message and manual text is treated as data. Off-topic requests beyond accessories and the guardrails against instruction overrides are incomplete here | **Partial**, see below |
| V. Decisions on Record | The README gains the framework, model, prompt strategy and limitations | Pass |
| Technical Constraints | uv and `uv.lock`, `.env.example` for settings, and each dependency serves a current requirement | Pass |
| Delivery Workflow | Incremental commits with no force-push. The example conversations come from real runs of this agent | Pass |

**Post-design re-check**: Pass, with the Principle IV exception below.

## Project Structure

### Documentation (this feature)

```text
specs/002-store-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── agent-tools.md
│   └── chat-changes.md
└── tasks.md             # Created by /speckit-tasks
```

### Source Code (repository root)

```text
src/emporio/
├── agent/
│   ├── contract.py      # Adds end_conversation, stricter details validation
│   ├── factory.py       # Registers the store agent as the default
│   └── store/
│       ├── agent.py     # Agent wiring, event loop, respond and end_conversation
│       ├── prompt.py    # Persona, section 7 guidance, clarifications, date and business hours
│       ├── providers.py # Primary and fallback models
│       └── trace.py     # Run messages to ReplyDetails
├── tools/
│   ├── catalog.py       # search_products, get_product
│   ├── payments.py      # payment_terms, with no model or database involved
│   ├── orders.py        # get_order_status and the identity check
│   ├── policies.py      # policy_lookup
│   ├── conversations.py # find_open_conversation, finish_conversation
│   └── complaints.py    # register_complaint
├── data/
│   ├── policy_index.py  # Existing
│   ├── store_db.py      # Opens data/emporio.sqlite, the only module that does
│   └── conversation_store.py  # Sessions, stored conversations and masking
├── safety/sanitize.py   # FR-018, plus a helper for logging
└── chat/                # Modal, logging, FR-017 and FR-020

scripts/
├── seed_db.py           # Creates the new tables, keeping their rows
└── check_agent.py       # SC-001 on the real model

tests/
├── unit/                # Tools, payments, masking, sessions, trace
├── contract/            # Interface rules for the store agent
└── integration/         # Modal and chat flows
```

**Structure Decision**: Tools sit outside `agent/store/` and know nothing about Pydantic AI beyond their registration,
so they can be tested as plain functions and would not change if the agent were later split.

## Complexity Tracking

| Exception | Why | What was rejected |
|---|---|---|
| Principle IV is partial: general off-topic requests and instruction overrides | The confirmed scope covers accessories only, and the guardrails belong to the evaluation stage in `docs/draft-check-list.md`. The draft agent failed an injection test, so this must be closed before delivery | Adding guardrails here, which goes beyond the confirmed scope |

## Implementation Notes for Tasks

- Add `make db` as a prerequisite of `make run` and `make run-dev`, because `data/emporio.sqlite` isn't committed
  and the agent needs it.
- Set `PYDANTIC_AI_NO_BANNER=1` before importing Pydantic AI, because it prints a promotional banner otherwise.
- Confirm that Pydantic AI runs synchronous tools off the event loop. If it doesn't, a slow tool would stall every
  other session, and the tools must be wrapped with `asyncio.to_thread`.
- Update the chat test that clicks "Nova conversa", which now opens the modal first.
- Tests that assert the default agent is the stand-in change with FR-001, and `specs/001-streamlit-chat/quickstart.md`
  now needs `EMPORIO_AGENT=stand_in`.
- Update `docs/corner-cases/store-data.md` to require both the email and the phone.
- Remove from `docs/pending-updates.md` what this feature completes.
- Add to the README: the decisions in [research.md](research.md), and these limitations: masking can miss unusual
  formats, stored conversations are never deleted automatically despite manual section 9, complaints have no screen
  for the store's team yet, nothing limits repeated guesses at an order's phone and email, and a finished conversation
  stays on screen until the next message.
