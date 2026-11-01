---

description: "Task list for the customer chat with troubleshooting view"
---

# Tasks: Customer Chat with Troubleshooting View

**Input**: Design documents from `/specs/001-streamlit-chat/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included, because the plan and [contracts/agent-interface.md](contracts/agent-interface.md)
define them. Write each test first and confirm it fails before implementing.

**Commits**: Commit each subject as soon as it is ready, before starting the next one, using
Conventional Commits and explicit paths. Do not push.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to (US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Make the package installable and the tools runnable. The Streamlit, python-dotenv and pytest
dependencies are already in `pyproject.toml` and `uv.lock`, so do not add them again.

- [X] T001 Create empty `src/emporio/__init__.py`, `src/emporio/agent/__init__.py`, `src/emporio/safety/__init__.py` and `src/emporio/chat/__init__.py`. Add to `pyproject.toml` a `[build-system]` section with `requires = ["setuptools>=77"]` and `build-backend = "setuptools.build_meta"`, add `*.egg-info/` to `.gitignore`, run `uv lock` and `make setup`, and confirm `uv run python -c "import emporio"` succeeds
- [X] T002 Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]` to `pyproject.toml`, and create the `tests/contract/`, `tests/unit/` and `tests/integration/` folders
- [X] T003 [P] Create `.streamlit/config.toml` with `browser.gatherUsageStats = false`, `client.showErrorDetails = "none"`, `client.toolbarMode = "minimal"` and `server.address = "localhost"`
- [X] T004 [P] Create `.env.example` documenting `EMPORIO_AGENT` (`stand_in`, the default), `EMPORIO_TROUBLESHOOTING` (`0` or `1`, default `0`) and `EMPORIO_REPLY_TIMEOUT_SECONDS` (positive number, default `60`), following [contracts/chat-application.md](contracts/chat-application.md)
- [X] T005 Add to `Makefile`, and to its `.PHONY` list, the targets `run` (depends on `setup`, starts `streamlit run src/emporio/chat/app.py`), `run-dev` (the same with `EMPORIO_TROUBLESHOOTING=1` and `--client.showErrorDetails=full`) and `test` (depends on `setup`, runs `pytest`), each with a `##` help comment and activating `$(VENV)` as the other targets do

**Checkpoint**: `make setup` and `import emporio` work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The agent interface, stand-in, sanitizer and settings that every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests

- [X] T006 [P] Write contract tests in `tests/contract/test_agent_interface.py`: a fresh Python process importing `emporio.agent` does not load `streamlit`; every stand-in command in [contracts/agent-interface.md](contracts/agent-interface.md) returns a valid `AgentReply` or does what its row says; the same input gives the same output; and `respond` returns an answer with no chat running (SC-008). Use a short delay override or a mocked sleep for `/lento`
- [X] T007 [P] Write sanitizer tests in `tests/unit/test_sanitize.py`: planted `.env` and sensitive-looking environment values and values under sensitive key names are removed from text, nested dictionaries including their keys, lists and exception text; model names and very short values are kept (FR-017, SC-006)
- [X] T008 [P] Write settings and agent selection tests in `tests/unit/test_config.py`: defaults, valid values, each invalid value naming its setting without showing values from private settings, and an unknown `EMPORIO_AGENT` reported as a configuration error with no fallback to the stand-in (FR-012, FR-020)

### Implementation

- [X] T009 [P] Define in `src/emporio/agent/contract.py` the `Agent` Protocol (`name`, `is_simulated`, `respond(conversation_id, message) -> AgentReply`) and standard-library frozen dataclasses `AgentReply`, `ReplyDetails`, `Step` and `Source`, with the fields and rules in [data-model.md](data-model.md): `Step.kind` is "`tool`, `retrieval`, `model` or `reasoning`", `Step.status` is "`ok` or `error`", `Step.duration_ms` is "Not negative", and `Source.kind` is "`data`, `policy` or `other`". Import no Streamlit
- [X] T010 Implement in `src/emporio/agent/stand_in.py` the stand-in agent with `is_simulated = True`, no model or store data, deterministic and safe across threads, handling a simple reply plus `/ferramenta`, `/politica`, `/fallback`, `/raciocinio`, `/grande`, `/incompleto`, `/sem-detalhes`, `/sensivel` (fake API key only, in a step result and an error), `/erro` and `/lento` as listed in [contracts/agent-interface.md](contracts/agent-interface.md) (depends on T009)
- [X] T011 [P] Implement in `src/emporio/safety/sanitize.py` the removal of every value from `.env` and sensitive-looking environment variables, except model names and very short values, and of anything under a sensitive key name, over text and JSON-compatible values including dictionary keys (see [research.md](research.md), section 8)
- [X] T012 [P] Implement in `src/emporio/config.py` reading and validating `EMPORIO_AGENT`, `EMPORIO_TROUBLESHOOTING` and `EMPORIO_REPLY_TIMEOUT_SECONDS` once at startup, loading `.env` with python-dotenv without overriding the environment, and raising a configuration error that names the invalid setting without its value
- [X] T013 Implement in `src/emporio/agent/factory.py` selecting the agent from `EMPORIO_AGENT`, reporting an unknown agent or one that cannot start as a configuration error, and never falling back to the stand-in (depends on T010, T012)

**Checkpoint**: `make test` passes for the contract, sanitizer and settings tests, with no chat running.

---

## Phase 3: User Story 1 - Chat with the store's assistant (Priority: P1) 🎯 MVP

**Goal**: A person exchanges messages in Portuguese with the stand-in, with earlier messages kept, and agent failures shown as a friendly message.

**Independent Test**: Start the application with the stand-in agent, exchange several messages, and confirm that each reply appears under its message, in order, with the earlier messages still visible.

### Tests for User Story 1

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T014 [P] [US1] Write tests in `tests/unit/test_conversation.py` for: message validation (blank rejected; "1 to 2,000 characters after trimming", with exactly 2,000 accepted and over 2,000 kept in `rejected_draft`); state moving `idle --> waiting --> idle`; a blank answer or exception giving outcome `failed`; a timeout giving `timed_out` and discarding the late result; an answer containing a secret being sanitized; and details discarded when troubleshooting is off
- [X] T015 [P] [US1] Write `AppTest` flows in `tests/integration/test_chat_flow.py` for: a 20-message conversation in order with the same conversation identifier (SC-002); a new conversation clearing messages and changing the identifier (FR-004); `**negrito** <b>teste</b>` shown literally (FR-021); blank messages not sent; the over-limit panel's error, edit, send and discard (FR-006); `/erro` and a timeout showing the friendly message with both WhatsApp numbers and the email, no technical text, and a usable chat (FR-008, SC-007); two separate `AppTest` sessions not sharing messages (SC-009); and no internal details in the page with troubleshooting off (FR-016). Set `EMPORIO_REPLY_TIMEOUT_SECONDS` low for the timeout test

### Implementation for User Story 1

- [X] T016 [US1] Implement in `src/emporio/chat/conversation.py` the `Conversation` and `Turn` types from [data-model.md](data-model.md), with a random unique `id`, `state`, `rejected_draft` and message validation, storing `details` "only in troubleshooting mode" (FR-003, FR-006, FR-016)
- [X] T017 [US1] Add to `src/emporio/chat/conversation.py` the guarded agent call: run `respond` in a daemon thread, wait up to the configured limit, catch every exception, treat a blank answer as a failure, discard late results, measure `elapsed_ms`, and sanitize the answer and details as soon as they return and before storing them (FR-008, FR-017; see [research.md](research.md), sections 5 and 8)
- [X] T018 [US1] Implement in `src/emporio/chat/app.py` the chat page: settings read at startup, one shared agent instance across sessions with `st.cache_resource`, the conversation held in `st.session_state`, messages rendered with `st.text` only, Portuguese text per [contracts/chat-application.md](contracts/chat-application.md), and a new conversation button available only in `idle` (FR-001 to FR-004, FR-007, FR-021)
- [X] T019 [US1] Add to `src/emporio/chat/app.py` the two-pass flow: the first pass stores the message and reruns with `st.chat_input` disabled and a spinner visible, and the second calls the agent, stores the result and reruns with input enabled, showing the friendly failure text from [contracts/chat-application.md](contracts/chat-application.md) on `failed` or `timed_out` (FR-005, FR-008; see [research.md](research.md), section 3)
- [X] T020 [US1] Add to `src/emporio/chat/app.py` the over-limit panel, without `max_chars` on the input: a Portuguese error with the message's length and the 2,000-character limit, a text area with the full text, and Enviar and Descartar buttons, revalidating on send (FR-006; see [research.md](research.md), section 4)

**Checkpoint**: `make test` passes and `make run` gives a working chat with no internal details.

---

## Phase 4: User Story 2 - See how each reply was produced (Priority: P2)

**Goal**: In troubleshooting mode, each reply has expandable details showing steps, sources, model, provider, fallback use, timing and errors, with no secrets.

**Independent Test**: Start the application in troubleshooting mode with the stand-in agent, send a message that triggers a simulated tool call and another that triggers a simulated failure, and confirm that both replies have complete details. Then start it in normal mode and confirm that the details are not available.

### Tests for User Story 2

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T021 [P] [US2] Write `AppTest` flows in `tests/integration/test_troubleshooting.py`, with `EMPORIO_TROUBLESHOOTING=1`, for: `/ferramenta` showing a step's inputs, result and duration with a `data` source, model, provider and total time; `/politica` and `/fallback`; a simple message stating that no tools or sources were used; `/sem-detalhes` and `/incompleto` marked unavailable and incomplete (FR-015); `/erro` and a timeout having details while the customer text stays friendly (SC-004); `/sensivel` showing the fake key nowhere in the page (SC-006); and `/grande` showing the summary and a button opening the modal. Also confirm that with troubleshooting off none of this appears and the page has no control to turn it on (FR-013, FR-016)

### Implementation for User Story 2

- [X] T022 [US2] Add to `src/emporio/chat/conversation.py` the setting of `details_state` to `complete`, `incomplete` or `unavailable`, treating missing or malformed details as `unavailable` without blocking the answer, and building sanitized details in the chat for `failed` and `timed_out` turns (FR-015, SC-004)
- [X] T023 [US2] Implement in `src/emporio/chat/details_view.py` a collapsed expander for each reply with the model, provider, fallback use, total time, sources and details state, one nested expander per step, and an explicit statement when no tools or sources were used (FR-014, FR-015)
- [X] T024 [US2] Add to `src/emporio/chat/details_view.py` the large details handling: over 10 steps or 6,000 sanitized characters, show the summary and a button opening an `st.dialog` with one expander per part, and shorten values over 2,000 characters inline with a marker, with the full sanitized value in the modal (see [research.md](research.md), section 6)
- [X] T025 [US2] Call the details view from `src/emporio/chat/app.py` only when troubleshooting is on, with no control in the page to change it (FR-013, FR-016)

**Checkpoint**: `make test` passes and `make run-dev` shows details under every reply, including failures.

---

## Phase 5: User Story 3 - Start the application with one command (Priority: P3)

**Goal**: A developer or evaluator starts the chat from the README with one command, sees that replies are simulated, and gets a clear error when the agent cannot start.

**Independent Test**: On a clean checkout, follow the README to set up and start the application, confirm the chat opens and answers using the stand-in agent, and then repeat in troubleshooting mode.

### Tests for User Story 3

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T026 [P] [US3] Write `AppTest` flows in `tests/integration/test_startup.py` for: the simulated-replies notice showing with the stand-in (FR-012); and invalid `EMPORIO_AGENT`, `EMPORIO_TROUBLESHOOTING` and `EMPORIO_REPLY_TIMEOUT_SECONDS` each showing an error page naming the setting, with no chat and no private values (FR-020)

### Implementation for User Story 3

- [X] T027 [US3] Add to `src/emporio/chat/app.py` the visible Portuguese notice, shown whenever the selected agent has `is_simulated` set to true (FR-012)
- [X] T028 [US3] Add to `src/emporio/chat/app.py` the startup error page for configuration errors from `src/emporio/config.py` and `src/emporio/agent/factory.py`, naming the setting and stopping before the chat renders (FR-012, FR-020)
- [ ] T029 [US3] Add to `README.md` the setup and run instructions for `make setup`, `make run`, `make run-dev` and `make test`, the settings in `.env.example`, and the stand-in commands for manual testing (FR-019, SC-001)

**Checkpoint**: All user stories work on their own, and an evaluator can start the chat from the README.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Record the decisions and validate the feature end to end.

- [ ] T030 Update `README.md` with the decisions in [research.md](research.md) (Principle V). Under Known Limitations, remove the Draft label from the crash details item, and state that the troubleshooting view shows customer data unmasked, because the data is fictional and the mode is for local use, and that real customer data would require masking or restricted access
- [ ] T031 Run `make test`, and confirm that nothing under `src/emporio/agent/` imports Streamlit and that nothing writes conversations or details to disk (FR-018) by reviewing `src/emporio/`
- [ ] T032 Run every check in [quickstart.md](quickstart.md) in a real browser, including nested expanders and the modal, which `AppTest` cannot show, and fix anything that fails in the file responsible

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T002 follows T001 because both edit `pyproject.toml`.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational.
- **User Story 2 (Phase 4)**: Depends on Foundational and on US1, because the details sit under replies in the chat page.
- **User Story 3 (Phase 5)**: Depends on Foundational and on the chat page from T018.
- **Polish (Phase 6)**: Depends on all user stories.

### Within Each User Story

- Tests are written first and fail before implementation.
- `conversation.py` comes before `details_view.py`, and both before their use in `app.py`.
- T016 to T020, T022 to T025 and T027 to T028 run in order, because they share files.

### Parallel Opportunities

- Setup: T003 and T004.
- Foundational tests: T006, T007 and T008.
- Foundational implementation: T009, T011 and T012.
- Story tests: T014 and T015.

## Parallel Example: Foundational Phase

```text
Task: "Write contract tests in tests/contract/test_agent_interface.py"
Task: "Write sanitizer tests in tests/unit/test_sanitize.py"
Task: "Write settings and agent selection tests in tests/unit/test_config.py"

Task: "Define the Agent Protocol and dataclasses in src/emporio/agent/contract.py"
Task: "Implement src/emporio/safety/sanitize.py"
Task: "Implement src/emporio/config.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational.
2. Complete User Story 1.
3. **Stop and validate**: run `make test`, then the customer mode checks in [quickstart.md](quickstart.md).

### Incremental Delivery

1. Setup and Foundational give a tested interface, stand-in and sanitizer.
2. User Story 1 adds the working chat, which is the MVP.
3. User Story 2 adds the troubleshooting view.
4. User Story 3 adds the notice, the startup errors and the README instructions.
5. Polish records the decisions and runs the full validation.
