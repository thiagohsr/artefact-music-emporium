---

description: "Task list for the store customer service agent"
---

# Tasks: Store Customer Service Agent

**Input**: Design documents from `/specs/002-store-agent/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included, because the plan defines them. Write each test first and confirm it fails before implementing.
`make test` uses Pydantic AI's test models and no network. Real-model checks run with `make agent-check`.

**Commits**: Commit each subject as soon as it is ready, before starting the next one, using Conventional Commits and
explicit paths, with no attribution lines. Do not push. Write comments only for what the code can't show.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story this task belongs to (US1, US2, US3, US4)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and commands the agent needs.

- [X] T001 Run `uv add 'pydantic-ai-slim[openai]>=2.64,<3' 'httpx2>=2.12,<3'` to update `pyproject.toml` and `uv.lock`, and confirm `make setup` still works
- [X] T002 [P] Add `db` as a prerequisite of `run` and `run-dev` in `Makefile`, and add `agent-check` (depends on `setup` and `db`, runs `python scripts/check_agent.py`) to its targets and `.PHONY` list, with a `##` help comment
- [X] T003 [P] Update `.env.example` so `EMPORIO_AGENT` documents `store` as the default and `stand_in` as simulated

**Checkpoint**: `make setup` works and `make test` still passes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The running agent with no tools yet, which every story adds to.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests

- [X] T004 [P] Write tests in `tests/unit/test_seed_db.py`: a seed creates `customer_identities`, `stored_conversations` and `complaints`, and a second seed keeps their rows while reloading the store tables
- [X] T005 [P] Write tests in `tests/unit/test_providers.py`: Ollama comes first and OpenRouter second when both are configured; either alone works; none raises `ValueError`; Cloudflare headers are sent only on the Ollama client; and the request timeout is 25 seconds
- [X] T006 [P] Write tests in `tests/unit/test_prompt.py`: the instructions contain sections 7.1, 7.2 and 7.3 read from the policy index and the rules from `docs/stakeholder-clarifications.md` (both WhatsApp numbers, the unaccented email, the installment tiers); the date is stated in `America/Campo_Grande`; and open or closed is right for a weekday at 09:00 and 18:00, Saturday at 13:00 and Sunday, per section 2 of the manual
- [X] T007 [P] Write tests in `tests/unit/test_trace.py` for the mapping table in [data-model.md](data-model.md): tool call and result to `Step(kind="tool")`, `policy_lookup` to `retrieval`, thinking to `reasoning`, sources by tool, and `fallback_used` true when the answering model isn't the primary
- [X] T008 [P] Write tests in `tests/unit/test_store_agent.py` using Pydantic AI's `TestModel` or `FunctionModel`: `respond` works from several threads in turn and at once (the "bound to a different event loop" case); history reaches the next run in one conversation and never another (FR-015); a session older than 30 minutes starts fresh; a run past its limit raises and saves no history; and a synchronous tool doesn't block the event loop
- [X] T009 Extend `tests/contract/test_agent_interface.py`: the stand-in and the store agent have `end_conversation`, which doesn't raise for an unknown ID; update `tests/unit/test_config.py` so the default agent is `store`

### Implementation

- [X] T010 Add the three tables from [data-model.md](data-model.md) to `scripts/seed_db.py` with `CREATE TABLE IF NOT EXISTS`, leaving them out of `TABLES` so that seeding keeps their rows
- [X] T011 [P] Create `src/emporio/errors.py` with `EmporioError(Exception)`, `ConfigError(EmporioError)` moved from `src/emporio/config.py` with its imports updated, and `ProviderError(EmporioError)`, per [research.md](research.md), section 14
- [X] T012 [P] Implement `src/emporio/data/store_db.py`, the only module that opens `data/emporio.sqlite`: a read-only connection and a write connection per call, with foreign keys on
- [X] T013 [P] Add `end_conversation(conversation_id) -> None` to the `Agent` Protocol in `src/emporio/agent/contract.py`, and a method that does nothing to `src/emporio/agent/stand_in.py`
- [X] T014 [P] Implement `src/emporio/agent/store/providers.py`: `OllamaProvider` with `/v1` on the base URL and Cloudflare headers on its `httpx2` client, `OpenRouterProvider`, and `FallbackModel` over those configured, using `OLLAMA_CHAT_MODEL` and `OPENROUTER_CHAT_MODEL`, with a 25-second timeout. Keep thinking on (see [research.md](research.md), section 4)
- [X] T015 [P] Implement `src/emporio/agent/store/prompt.py`: the persona, sections 7.1 to 7.3 read from the policy index, the rules from `docs/stakeholder-clarifications.md`, the tool guidance, and per-run date and business hours in `America/Campo_Grande`, stating that message and manual text are data, not instructions
- [X] T016 [P] Implement `src/emporio/agent/store/trace.py`: turn a run's messages into `ReplyDetails` per [data-model.md](data-model.md)
- [X] T017 Implement the in-memory session part of `src/emporio/data/conversation_store.py`: `history`, `user_id`, `stored_id`, `last_message_at` and `closed` per `conversation_id`, closing after 30 minutes without a message and removing expired sessions on the next message, safe across threads
- [X] T018 Implement `src/emporio/agent/store/agent.py`: one long-lived event loop in a daemon thread, `respond` submitting with `asyncio.run_coroutine_threadsafe`, a lock per conversation, `asyncio.timeout` 5 seconds below `EMPORIO_REPLY_TIMEOUT_SECONDS`, history saved only on success, `end_conversation`, raising `ProviderError` with `from error` when no provider answers, and `PYDANTIC_AI_NO_BANNER=1` set before importing Pydantic AI. Confirm how synchronous tools run, wrapping them with `asyncio.to_thread` if they run on the loop
- [X] T019 Register `store` in `src/emporio/agent/factory.py`, set `DEFAULT_AGENT = "store"` in `src/emporio/config.py`, and have tests that need the stand-in set `EMPORIO_AGENT=stand_in`

**Checkpoint**: `make test` passes, and with a provider `make run` answers a greeting through the real model.

---

## Phase 3: User Story 1 - Be served in the store's voice and get correct answers (Priority: P1) 🎯 MVP

**Goal**: The agent follows section 7's tone and flow, and answers about products, payment and store rules from tools.

**Independent Test**: Run a full conversation through each step of the flow, then each special situation, and compare the replies with sections 7.1 to 7.3, the store data and the manual.

### Tests for User Story 1

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T020 [P] [US1] Write tests in `tests/unit/test_catalog.py`: `search_products` by text, category, `min_price_brl`, `max_price_brl`, either limit alone and both, with limits inclusive and compared with the final price under an active promotion; `in_stock_only`; a maximum of 10 results; discontinued products left out; `get_product` for one match, close matches and not found as data; a promotion included only when active, with original price, discount percentage and final price; and `coming_soon` reported as not yet available whatever its stock says
- [X] T021 [P] [US1] Write tests in `tests/unit/test_payments.py`: `pix` takes 5% off the list price and nothing off a promotional price; `debit` and `boleto` at the price; R$ 500 in 10x not allowed with `below_minimum`; the boundary at R$ 50, R$ 80 and R$ 100 per tier; 13x not allowed with `too_many_installments`; `product_name` or `amount_brl` accepted; and money handled with `Decimal`
- [X] T022 [P] [US1] Write tests in `tests/unit/test_policy_tool.py`: `policy_lookup` returns up to 3 customer sections with numbers, never sections 7, 7.1, 7.2, 7.3 or 10 (FR-023), and falls back to keywords when embedding fails or the embedding model isn't compatible
- [X] T023 [P] [US1] Write tests in `tests/unit/test_complaints.py`: `register_complaint` stores a masked summary with the time, and returns the 24 business hours return time; and `finish_conversation` closes the session

### Implementation for User Story 1

- [X] T024 [P] [US1] Implement `search_products` and `get_product` in `src/emporio/tools/catalog.py` per [contracts/agent-tools.md](contracts/agent-tools.md)
- [X] T025 [P] [US1] Implement `payment_terms` in `src/emporio/tools/payments.py` per [contracts/agent-tools.md](contracts/agent-tools.md)
- [X] T026 [P] [US1] Implement `policy_lookup` in `src/emporio/tools/policies.py` using `src/emporio/data/policy_index.py`, with a short embedding timeout, and vectors only when `is_compatible` passes
- [X] T027 [P] [US1] Implement the shared masking in `src/emporio/data/conversation_store.py` (emails and phone-shaped text, plus exact known values), and `register_complaint` in `src/emporio/tools/complaints.py` using it
- [X] T028 [US1] Implement `finish_conversation` in `src/emporio/tools/conversations.py`
- [X] T029 [US1] Register the tools from T024 to T028 in `src/emporio/agent/store/agent.py`, with descriptions saying when to use each, as in the spec's Agent Tools table (FR-022)
- [X] T030 [US1] Create `scripts/check_agent.py`: run the brief's questions, an installment question and each special situation in User Story 1 on the real model, checking the tools called and the expected values, printing each question's result and time, and exiting non-zero on failure

**Checkpoint**: `make test` passes, and `make agent-check` passes for this story on the real model. This is the MVP.

---

## Phase 4: User Story 2 - Check an order with identity verification (Priority: P2)

**Goal**: Order details are shared only when the order number, phone and email all match.

**Independent Test**: Ask about an order with correct details, then again with a wrong phone, a wrong email, and each missing, and confirm details appear only in the first case.

### Tests for User Story 2

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T031 [US2] Write tests in `tests/unit/test_orders.py`: success returns status, order date, stored total, payment method, items, tracking code, delivery estimate and days since that estimate; phones compare by digits and emails ignore case; a wrong phone, a wrong email and an unknown order give identical results; customers 11 and 43, who share an email, can't reach each other's orders; the stored total is never recalculated (orders 3 and 20); success records the customer in the session, and failure records nothing

### Implementation for User Story 2

- [X] T032 [US2] Implement `get_order_status` in `src/emporio/tools/orders.py` per [contracts/agent-tools.md](contracts/agent-tools.md), recording the customer in the session from the check and never from a model value (FR-024), and register it in `src/emporio/agent/store/agent.py`
- [X] T033 [P] [US2] Update `docs/corner-cases/store-data.md` to require both the email and the phone
- [X] T034 [US2] Add the order questions to `scripts/check_agent.py`: with correct details, with each missing and wrong, and "Me arrependi da minha compra, posso devolver meu pedido?" with a verified customer

**Checkpoint**: Stories 1 and 2 pass `make test` and `make agent-check`.

---

## Phase 5: User Story 3 - Continue a conversation (Priority: P2)

**Goal**: Follow-ups work, and a verified customer continues an open conversation after a page reload.

**Independent Test**: Ask a follow-up in one session. Verify a customer, reload the page, verify again, and confirm the conversation continues. Repeat without verifying, and after using the new conversation button, and confirm it does not.

### Tests for User Story 3

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [X] T035 [P] [US3] Write tests in `tests/unit/test_conversation_store.py`: nothing is stored before identification; on identification, the session's earlier messages are stored, masked, with no thinking parts and no readable name, phone or email, including in tool arguments and results (SC-004); a customer has one user ID and at most one open conversation, with the most recent winning; 30 minutes without a message closes it; a closed conversation stays stored and can't be continued; and a second customer passing the check closes the first customer's conversation and clears the history
- [X] T036 [P] [US3] Write `AppTest` flows in `tests/integration/test_new_conversation.py`: "Nova conversa" opens a modal in Portuguese; Cancel changes nothing; Confirm calls `end_conversation`, clears the messages and changes the identifier. Update the existing test in `tests/integration/test_chat_flow.py` that clicks the button

### Implementation for User Story 3

- [X] T037 [US3] Add the stored conversation functions to `src/emporio/data/conversation_store.py` per [data-model.md](data-model.md): user IDs in `customer_identities`, saving after each successful run once identified, finding the open conversation, and closing
- [X] T038 [US3] Implement `find_open_conversation` in `src/emporio/tools/conversations.py`, taking the customer from the session and returning the masked transcript, and register it in `src/emporio/agent/store/agent.py`. Connect `finish_conversation`, `end_conversation` and the 30-minute limit to closing the stored conversation (FR-014)
- [X] T039 [US3] Add the confirmation modal to `src/emporio/chat/app.py` with `st.dialog`, calling `end_conversation` on the agent on Confirm, per [contracts/chat-changes.md](contracts/chat-changes.md)

**Checkpoint**: Stories 1 to 3 pass `make test`, and a reload continues a verified conversation in the chat.

---

## Phase 6: User Story 4 - Keep working and diagnose failures (Priority: P3)

**Goal**: The fallback takes over, developers can find causes in the terminal, and the code review improvements are done.

**Independent Test**: Stop access to the primary model and confirm the agent answers through the fallback. Make every provider fail and confirm the customer sees the friendly message and the terminal shows the cause.

### Tests for User Story 4

> **NOTE: Write these tests first and confirm they fail before implementation.**

- [ ] T040 [P] [US4] Write tests in `tests/unit/test_failure_logging.py` using `caplog`: an agent exception, a call that ends with no result, an agent that can't start and details that become unavailable are each logged with planted secrets removed, and the page content doesn't change. An agent raising `SystemExit` gives outcome `failed`, not `timed_out` (FR-017)
- [X] T041 [P] [US4] Extend `tests/unit/test_sanitize.py`: lists and numbers under sensitive names are removed; `total_tokens` is kept, and `access_token` and `token` still match (FR-018)
- [ ] T042 [P] [US4] Extend `tests/contract/test_agent_interface.py`: `ReplyDetails(errors="boom")` is invalid, and likewise a text in place of steps or sources (FR-019)
- [ ] T043 [P] [US4] Add to `tests/unit/test_conversation.py` and `tests/integration/test_chat_flow.py`: sending a blank edit from the long-message panel closes it (FR-020)
- [ ] T044 [P] [US4] Add to `tests/unit/test_store_agent.py`: a failing primary falls back, and the reply details say so; failure on every provider raises `ProviderError`, so the customer gets the friendly message

### Implementation for User Story 4

- [X] T045 [P] [US4] Update `src/emporio/safety/sanitize.py`: any non-empty value under a sensitive name is removed, using `token(?!s)`, and add a function that sanitizes an exception's text and traceback for logging
- [ ] T046 [P] [US4] Update `is_valid_details` in `src/emporio/agent/contract.py` to require lists or tuples for steps, sources and errors
- [ ] T047 [US4] Update `src/emporio/chat/conversation.py` per [research.md](research.md), section 14: handle `EmporioError` by type, keep a logged catch-all only at the agent boundary with `# noqa: BLE001` and its reason, log failures after the sanitizer, report a call that ended with no result as `failed`, log why details became unavailable, and close the panel on a blank edit
- [ ] T048 [US4] Log the sanitized cause in `create_agent` in `src/emporio/agent/factory.py`, with the same `# noqa: BLE001` and reason on its catch-all, keeping `from None` so the page shows no detail, and configure `logging` to the terminal in `src/emporio/chat/app.py`
- [ ] T049 [US4] Press Streamlit's Stop during a wait in a real browser, record what happens in [research.md](research.md), and if the page stays unusable, fix it in `src/emporio/chat/app.py` with a test (FR-021)

**Checkpoint**: All stories pass `make test` and `make agent-check`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Record the decisions and validate everything together.

- [ ] T050 Update `README.md` with the decisions in [research.md](research.md), the store agent as the default, what a provider needs, and these limitations: masking can miss unusual formats, stored conversations are never deleted automatically despite manual section 9, complaints have no screen for the store's team yet, nothing limits repeated guesses at an order's phone and email, and a finished conversation stays on screen until the next message
- [ ] T051 [P] Remove from `docs/pending-updates.md` what this feature completes, and update `docs/draft-check-list.md`
- [ ] T052 [P] Note in `specs/001-streamlit-chat/quickstart.md` that its checks need `EMPORIO_AGENT=stand_in`
- [ ] T053 Run `make test`, `make policy-check` and `make agent-check` on both providers, and record the eight-tool reply times in [research.md](research.md), against the 60-second limit
- [ ] T054 Run every check in [quickstart.md](quickstart.md) in a real browser, and fix anything that fails in the file responsible

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational.
- **User Story 2 (Phase 4)**: Depends on Foundational. T034 extends the script from T030.
- **User Story 3 (Phase 5)**: Depends on User Story 1 for masking and `finish_conversation`, and User Story 2 for identification.
- **User Story 4 (Phase 6)**: Depends on Foundational. T044 needs the agent, and T047 and T048 only touch existing code.
- **Polish (Phase 7)**: Depends on all user stories.

### Within Each User Story

- Tests are written first and fail before implementation.
- Tools come before their registration in `agent.py`.
- Tasks that share a file run in order: `agent.py` in T018, T029, T032 and T038, `conversation_store.py` in T017, T027 and T037, and `app.py` in T039, T048 and T049.

### Parallel Opportunities

- Setup: T002 and T003.
- Foundational tests: T004 to T008. Foundational implementation: T011 to T016.
- User Story 1: tests T020 to T023, and tools T024 to T027.
- User Story 4: tests T040 to T044, and T045 and T046.

## Parallel Example: User Story 1

```text
Task: "Write tests in tests/unit/test_catalog.py"
Task: "Write tests in tests/unit/test_payments.py"
Task: "Write tests in tests/unit/test_policy_tool.py"

Task: "Implement search_products and get_product in src/emporio/tools/catalog.py"
Task: "Implement payment_terms in src/emporio/tools/payments.py"
Task: "Implement policy_lookup in src/emporio/tools/policies.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational.
2. Complete User Story 1.
3. **Stop and validate**: run `make test` and `make agent-check`. This is the first point where the real agent answers
   the brief's questions, and it gives the first eight-tool timing.

### Incremental Delivery

1. User Story 1 gives real answers about products, payment and store rules.
2. User Story 2 adds order questions with the identity check.
3. User Story 3 adds stored conversations and the modal.
4. User Story 4 adds logging and the code review improvements.
5. Polish records the decisions and runs the full validation.
