# Contract: Chat Changes

What changes from [the chat application contract](../../001-streamlit-chat/contracts/chat-application.md).

## Commands

| Command | Result |
|---|---|
| `make run`, `make run-dev` | Also prepare the store database first |
| `make agent-check` | Runs the acceptance questions on the real model, and needs a provider |

## Settings

| Setting | Change |
|---|---|
| `EMPORIO_AGENT` | Gains `store`, the new default. `stand_in` stays available |
| `OLLAMA_CHAT_MODEL`, `OPENROUTER_CHAT_MODEL` | Read by the agent |

With no provider configured, the store agent can't start, and the existing error page names `EMPORIO_AGENT` (FR-012,
FR-020 of the chat spec).

## Nova conversa

Clicking the button opens a modal in Portuguese.

| Choice | Result |
|---|---|
| Confirm | Calls `end_conversation`, clears the messages and creates a new conversation identifier |
| Cancel | The modal closes and nothing changes |

## Logging

Errors go to the terminal through `logging`, after the sanitizer. Nothing new reaches the page.

| Where | What is logged |
|---|---|
| The guarded agent call | Exceptions, and a call that ended with no result |
| Agent start | The cause, with the page unchanged |
| Building reply details | Why they became unavailable |

## Long-message panel

Sending a blank edit closes the panel, like Descartar (FR-020).
