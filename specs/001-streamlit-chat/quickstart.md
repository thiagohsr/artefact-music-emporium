# Quickstart: Validate the Chat

Proves the feature works end to end. It needs no model, API key or store data.

## Prerequisites

uv installed, and a checkout of this branch.

## Automated checks

```bash
make test
```

Expected: all tests pass, covering the [agent interface](contracts/agent-interface.md), sanitizer and
chat flows.

## Customer mode

```bash
make run
```

Open <http://localhost:8501>.

| # | Do this | Expected | Covers |
|---|---|---|---|
| 1 | Look at the page | Portuguese text and a notice that replies are simulated | FR-007, FR-012 |
| 2 | Send several messages, up to 10 back and forth | All visible, in order, with no internal details | US1, SC-002, SC-007 |
| 3 | Send `**negrito** <b>teste</b>` | Displayed literally, without formatting | FR-021 |
| 4 | Send only spaces | Nothing is sent | FR-006 |
| 5 | Paste more than 2,000 characters and send, then shorten the text in the panel and send it | The agent is not called at first, an error in Portuguese shows the length and limit, and the full text is editable. The shortened message then sends normally | FR-006 |
| 6 | Send `/lento`, and try to send again while waiting | Input disabled and a spinner visible within 1 second, then the failure message after the limit | FR-005, FR-008, SC-003 |
| 7 | Send `/erro` | Friendly message with both WhatsApp numbers and the email, no technical text, and the chat still works | FR-008, SC-007 |
| 8 | Open a second browser window and send a message | Neither window shows the other's messages | SC-009 |
| 9 | Start a new conversation | Messages are cleared | FR-004 |
| 10 | Refresh the page | The conversation starts empty | Edge case |

## Troubleshooting mode

```bash
make run-dev
```

| # | Do this | Expected | Covers |
|---|---|---|---|
| 11 | Send `/ferramenta` and open the details | Step with inputs, result and duration, a `data` source, model, provider and total time | FR-014, SC-005 |
| 12 | Send a simple message | Details say no tools or sources were used | FR-015 |
| 13 | Send `/sem-detalhes` and `/incompleto` | Answer shown, details marked unavailable or incomplete | FR-015 |
| 14 | Send `/erro` | Details show the error, and the customer text stays friendly | US2 |
| 15 | Send `/sensivel` | The fake key is not shown in the chat or the details | FR-017, SC-006 |
| 16 | Send `/grande` | Summary and a button that opens a modal with expandable parts | Project owner's decision |

## Startup errors

```bash
EMPORIO_AGENT=unknown make run
```

Expected: an error page naming `EMPORIO_AGENT`, and no chat using the stand-in (FR-012, FR-020).
