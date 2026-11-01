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
