# Research: Store Customer Service Agent

Behavior marked **verified** was tested on 2026-11-01 with Pydantic AI 2.64.0 against `qwen3:8b` on the
self-hosted server and `openai/gpt-4o-mini` on OpenRouter. These tests used two stub tools, not the eight in the spec,
and each measurement is a small sample. There are no open clarifications.

## 1. Agent framework

**Decision**: Pydantic AI with one `Agent` and its built-in tool loop, using `pydantic-ai-slim[openai]`.

**Rationale**: Chosen by the project owner. Tools are typed Python functions, which matches the existing code.
**Verified**: on `qwen3:8b`, "Quanto fica o Takamine GD20 em 12x?" called the product tool and then the payment tool,
and gave the right value.

**Alternatives considered**: LangGraph, which is valid but mainly pays off with a graph, and this design has none.
A router with specialist agents, documented in the README as the next step if the evaluation shows the model picks
the wrong tools, following OpenAI's guidance to maximize a single agent first.

## 2. Running the agent from the chat's threads

**Decision**: The agent owns one long-lived event loop in a daemon thread. `respond` submits the run to it with
`asyncio.run_coroutine_threadsafe`.

**Rationale**: The chat calls `respond` from a new thread per reply. **Verified** that `run_sync` from a new thread
with a shared HTTP client fails with "bound to a different event loop", and that one long-lived loop fixes it,
including a follow-up from another thread and four replies at once.

**Alternatives considered**: A new client per reply, which gives up connection reuse to the self-hosted server.

## 3. Reply time limit

**Decision**: Each run has its own limit 5 seconds below `EMPORIO_REPLY_TIMEOUT_SECONDS`, using `asyncio.timeout`, and
each model request has a 25-second limit. History is saved only after a run succeeds.

**Rationale**: The chat's limit can't stop a running call. Without this, a late reply could enter the history of a
conversation the customer was told had failed, and the next message would run at the same time. A lock per
conversation also prevents that.

## 4. Models and thinking

**Decision**: `FallbackModel` with `qwen3:8b` through `OllamaProvider`, then OpenRouter. Thinking stays on. Cloudflare
headers go on the Ollama client only. The clients use `httpx2`, because Pydantic AI 2.64 deprecates `httpx` for these
providers.

**Rationale**: **Verified**: with the primary unreachable, the fallback answered through the tool in 4.6 s. With
thinking off the reply took 3.7 s instead of 7.3 s, but stated a made-up price of R$ 1,000 instead of the tool's
R$ 2,199. One sample isn't proof, but accuracy matters more than a few seconds. Passing `think: false` in the request
body had no effect through this API.

## 5. Tool failures

**Decision**: Expected results, such as a product not found or a failed order check, are returned as data. Only
unexpected errors raise.

**Rationale**: **Verified** that an exception in a tool fails the whole reply, so the customer gets the failure
message. That's right for a broken database, but wrong for "product not found".

## 6. Identity

**Decision**: `get_order_status` compares against the customer on that order, with phones compared by digits and
emails ignoring case. On success, the session records the customer. `find_open_conversation` and
`register_complaint` read the session, and take no customer value from the model.

**Rationale**: FR-008 and FR-024. Starting from the order handles the two customers who share an email. Phones are
unique in the data, with 50 across 50 customers.

**Limitation**: Nothing limits repeated guesses at an order's phone and email.

## 7. Stored conversations

**Decision**: Store Pydantic AI's message history as JSON once a customer is identified, without its thinking parts.
The earlier messages of that session are included. `find_open_conversation` returns the masked transcript as its tool
result.

**Rationale**: **Verified** that history survives a JSON round trip and continues correctly. A tool can't replace the
history of the run it's part of, so returning a transcript is the direct way to reach the earlier conversation.

`get_order_status` also includes the open conversation in its result after a successful check. **Verified**: left to the
model, `qwen3:8b` called `find_open_conversation` in only 1 of 5 runs, even when the verified result told it to.
`find_open_conversation` stays as the tool that does the lookup.

**System user ID**: A random ID in a table that maps it to `customer_id`, in the same database.

**Limitation**: This is pseudonymization, not anonymization, because whoever has the database file can follow the
mapping.

**Later improvement, raised by the project owner for a second phase**: derive the user ID as an HMAC of the
customer's phone and email with a secret kept outside the database, and drop the mapping table. Nothing stored would
then link a conversation to a customer, and the ID would be recomputed from what the customer provides at the order
check. It needs one more required secret, and losing it would orphan stored conversations.

## 8. Masking personal data

**Decision**: Before saving, replace the verified customer's exact name, phone and email, then any other email or
phone-shaped text, with placeholders. Tool arguments and results are included, since `get_order_status` receives the
phone and email.

**Rationale**: FR-011 and SC-004. Exact values catch the customer's own data in any format the database holds, and
patterns catch data they type about anything else. The in-memory history of the session stays unmasked, because the
agent needs it, and a continued conversation has only the masked version.

**Limitation**: Unusual formats and other people's names can slip through, which the README records.

## 9. Retention

**Decision**: No automatic deletion.

**Limitation**: Manual section 9 lets customers ask for their data to be deleted, and there's no way to do that yet.
The README records this.

## 10. Closing conversations

**Decision**: Sessions are keyed by `conversation_id` in the agent. `finish_conversation` and the 30-minute limit mark
the session closed, and the next message with that ID starts a fresh one. "Nova conversa" calls a new
`end_conversation` method on the interface. A stored conversation is treated as closed once 30 minutes have passed
since its last message, and expired sessions are removed when the next message arrives.

**Rationale**: The chat needs no reply-format change, and no background job is needed.

**Limitation**: After `finish_conversation`, the old messages stay on screen until the customer uses the button.

## 11. Sensitive names (FR-018)

**Decision**: Redact any non-empty value under a sensitive name, and change the pattern from `token` to `token(?!s)`.

**Rationale**: FR-018 extends redaction to lists and numbers, and without the change `total_tokens` would be redacted.
`access_token` still matches.

## 12. Business hours and dates

**Decision**: `prompt.py` works out the current date and whether the store is open in `America/Campo_Grande`, from the
hours in section 2 of the manual, and states it in the instructions for each run. Tools receive today's date for return
periods.

**Rationale**: FR-004 applies to these too: the model shouldn't work out dates or hours.

**Limitation**: Holidays and special dates aren't covered, because the manual doesn't list them.

## 13. Real-model acceptance

**Decision**: `scripts/check_agent.py`, run with `make agent-check`, asks the SC-001 questions on the real model. It
checks which tools were called and that the expected values appear in the answer.

**Rationale**: `make test` can't prove a real model picks the right tools, and SC-001 has to be repeatable. Full
scoring stays in the evaluation stage.

## 14. Exception pattern

**Decision**: Follow Ruff's `BLE001` across the project, as required by the project owner. Add `EmporioError(Exception)`
with `ConfigError` and `ProviderError` under it, in `src/emporio/errors.py`.

| Rule | Where |
|---|---|
| Catch specific errors | Everywhere by default |
| A broad catch, always logged, with `# noqa: BLE001` and its reason | Only at real boundaries: the guarded agent call, building reply details, and agent start |
| Translate library errors into our classes, with `raise ... from error` | Where the agent calls a provider |
| Expected results are data, not exceptions | Tools, as in section 5 |

**Rationale**: The classes derive from `Exception` because Python's `BaseException` also covers `KeyboardInterrupt` and
`SystemExit`. A catch-all has to stay at the boundary, because the contract lets an agent raise anything, and without it the
customer would get a crash instead of the friendly message.

**Alternatives considered**: A larger hierarchy now, which would add classes nobody handles differently. More can be
added when a caller needs to tell two failures apart. A separate branch later, which would mean reworking the agent code.

## 15. Streamlit's Stop button (FR-021)

**Finding**: **Verified** in Chrome that with `client.toolbarMode = "minimal"`, used by both `make run` and `make run-dev`, no
Stop control exists during a wait. It appears only with the developer toolbar. So nobody can press it, and no fix is needed.

