# Pending Updates

Changes to make later, with the moment each one becomes relevant.

## Exception handling

**When**: On the next branch, before the real agent is connected, because it can fail in many more ways
than the stand-in.

**Already sound, so keep**: The narrow catches for known failures, `ConfigError` naming a setting without
its value, the broad catches at the agent boundary, and customers seeing only the friendly message.

**Change**:

| Problem | Where | Current behavior | Change |
|---|---|---|---|
| Failures are not logged | The broad catches in `src/emporio/chat/conversation.py` and `src/emporio/agent/factory.py` | A `/erro` failure with troubleshooting off prints nothing, so the error is lost | Log them to the terminal with the standard `logging` module, after passing them through the sanitizer, because tracebacks can contain secrets |
| The startup cause is discarded | `create_agent` in `src/emporio/agent/factory.py` | `from None` keeps secrets off the page but also hides the reason an agent could not start | Keep the page as it is, and log the sanitized cause to the terminal |
| Sanitizing failures are silent | `_build_details` in `src/emporio/chat/conversation.py` | Details become `unavailable`, with no record of why | Log the failure |
| The wrong failure is reported | `_PendingCall` in `src/emporio/chat/conversation.py` | An agent raising `SystemExit` ends the thread with no result, which reports `timed_out` after 0 ms | When the thread has ended with no result, report `failed` |

Logging must stay in the terminal, because the app must not save conversations or details to disk
(FR-018), and nothing new may reach the page (FR-016).

**Decide in the agent spec**: Typed agent errors, such as a provider being unavailable. The stand-in has
only one simulated failure, so defining them now would be guesswork.

## Improvements for the real agent

**When**: While interacting with the real agent, which will show how much each one matters.

| Issue | Where | Current behavior |
|---|---|---|
| Lists and numbers under sensitive keys | `Sanitizer._clean_item` in `src/emporio/safety/sanitize.py` | Only string values are redacted under names like `api_key`, so `{"api_key": ["abc"]}` passes unchanged |
| `errors` given as a string | `is_valid_details` in `src/emporio/agent/contract.py` | It accepts `ReplyDetails(errors="boom")`, and the view prints it one character at a time |
| Blank edit in the long-message panel | `submit` in `src/emporio/chat/conversation.py` | Clearing the text and clicking Enviar does nothing visible, and the old error stays |

**Verify first**: Whether Streamlit's Stop button during a wait leaves the page disabled until a refresh.
A code review raised this, but it has not been reproduced.
