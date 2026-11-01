# Implementation Plan: Customer Chat with Troubleshooting View

**Branch**: `001-streamlit-chat` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-streamlit-chat/spec.md`

## Summary

Build a Streamlit chat in Brazilian Portuguese that calls the agent directly through one small,
UI-independent interface. A stand-in agent proves the chat and the failure paths before the real agent
exists. A troubleshooting mode, turned on only at startup, shows how each reply was produced in
expandable sections under the reply, and in a modal when the details are too large. Replies and details
are sanitized when they enter the chat layer, so secrets cannot reach the page.

## Technical Context

**Language/Version**: Python 3.13, managed with uv

**Primary Dependencies**: Streamlit 1.66+, python-dotenv (reads private values so they can be removed).
Dev: pytest. Build backend: setuptools. No agent framework, FastAPI or MCP in this feature.

**Storage**: None. Conversations live in browser session state, and nothing is written to disk. The
SQLite database is not used by this feature.

**Testing**: pytest for the contract, sanitizer and stand-in; Streamlit `AppTest` for chat flows
without a browser; [quickstart.md](quickstart.md) for the few checks that need a real browser.

**Target Platform**: Local run on macOS and Linux, bound to localhost.

**Project Type**: Single-process web application with a src-layout package.

**Performance Goals**: Progress visible within 1 second of sending (SC-003). Stand-in replies are
immediate except when simulating slowness.

**Constraints**: 2,000-character message limit and 60-second reply limit. Secrets never shown. Internal details never in the page unless troubleshooting mode is on. The agent package must not import Streamlit.

**Scale/Scope**: One process and a few simultaneous sessions, for local use and small demos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle or rule | How this feature complies | Status |
|---|---|---|
| I. Grounded Answers | No business answers come from this feature. The stand-in shows a visible notice and is never a silent replacement. Failure text uses the recorded contact rules: both WhatsApp numbers and the unaccented email | Pass |
| II. Right Source | Reply details record each step and the kind of source used, so routing can be observed and tested | Pass |
| III. Customer Privacy | Conversations are isolated and nothing is saved. Identity checks belong to the agent spec | Pass |
| IV. Persona and Scope | Customer-facing text is in Brazilian Portuguese in the store's tone. Message text is displayed as plain content, so it cannot act on the page | Pass |
| V. Decisions on Record | The README gains these decisions, the run commands and the interface limitation | Pass |
| Technical Constraints | Python and uv with a locked `uv.lock`, one-command start, `.env.example` for settings, no framework chosen here, and each dependency serves a current requirement | Pass |
| Delivery Workflow | Work stays on a feature branch with incremental commits. The stand-in's visible notice keeps simulated replies from passing as example conversations | Pass |

**Post-design re-check**: Pass. The design adds no principle exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/001-streamlit-chat/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── agent-interface.md
│   └── chat-application.md
└── tasks.md             # Created by /speckit-tasks
```

### Source Code (repository root)

```text
.streamlit/config.toml       # Safe server defaults
src/emporio/
├── config.py                # Reads and validates startup settings
├── agent/                   # No Streamlit imports allowed
│   ├── contract.py          # Agent interface and reply data types
│   ├── factory.py           # Selects the agent and reports configuration errors
│   └── stand_in.py          # Scripted agent for tests and early development
├── safety/
│   └── sanitize.py          # Removes secrets
└── chat/
    ├── app.py               # Streamlit entry point
    ├── conversation.py      # Session state and the guarded call to the agent
    └── details_view.py      # Expandable sections and modal

tests/
├── contract/                # Interface rules, including no Streamlit import
├── unit/                    # Sanitizer, stand-in and conversation
└── integration/             # Chat flows with AppTest
```

**Structure Decision**: A single src-layout package, as chosen by the project owner. The `agent`,
`safety` and `chat` packages keep the dependency direction one way: `chat` uses the other two, and
`agent` never imports `chat`. The real agent will later live under `src/emporio/agent/` and be added to
the factory. Existing `scripts/seed_db.py` stays where it is.

## Implementation Notes for Tasks

- When creating `src/emporio/`, add a `[build-system]` section to `pyproject.toml` with
  `requires = ["setuptools>=77"]` and `build-backend = "setuptools.build_meta"`, so `uv sync` installs
  the package. Add `*.egg-info/` to `.gitignore`, then update `uv.lock`.
- Add `make run`, `make run-dev` and `make test`, plus a `.env.example` with the new settings.
- Update the README with run instructions and the decisions in [research.md](research.md). Under known
  limitations, state that the troubleshooting view shows customer data unmasked, because the data is
  fictional and the mode is for local use, and that real customer data would require masking or
  restricted access.
- Follow [contracts/](contracts/) and [data-model.md](data-model.md) for all behavior details.
