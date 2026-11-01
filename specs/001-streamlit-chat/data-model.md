# Data Model: Customer Chat with Troubleshooting View

All of this lives in memory, in browser session state. Nothing is written to a database.

## Types the agent returns

Defined in [contracts/agent-interface.md](contracts/agent-interface.md).

### AgentReply

| Field | Type | Rules |
|---|---|---|
| `answer` | text | Required and not blank; a blank answer counts as a failure |
| `details` | ReplyDetails or nothing | Missing or invalid details do not block the answer (FR-015) |

### ReplyDetails

| Field | Type | Rules |
|---|---|---|
| `steps` | list of Step | In execution order; may be empty |
| `sources` | list of Source | May be empty |
| `model` | text or nothing | For example `qwen3:8b` |
| `provider` | text or nothing | For example `ollama` |
| `fallback_used` | true or false | True when a fallback provider answered |
| `errors` | list of text | Failures that did not stop the reply |
| `complete` | true or false | False when the agent knows the details are partial |

### Step

| Field | Type | Rules |
|---|---|---|
| `name` | text | Required, such as a tool name |
| `kind` | `tool`, `retrieval`, `model` or `reasoning` | Required |
| `status` | `ok` or `error` | Required |
| `duration_ms` | number or nothing | Not negative |
| `inputs` | JSON-compatible value | May be empty |
| `result` | JSON-compatible value | Reasoning text goes here for `reasoning` steps |
| `error` | text or nothing | Set when `status` is `error` |

### Source

| Field | Type | Rules |
|---|---|---|
| `kind` | `data`, `policy` or `other` | Required; shows routing for Principle II |
| `name` | text | Required, such as `products` or `Section 4.1` |

## Types the chat stores

### Conversation

| Field | Type | Rules |
|---|---|---|
| `id` | text | Random and unique; a new conversation gets a new one (FR-003, FR-004) |
| `turns` | list of Turn | In order; one person's message and its outcome |
| `state` | see below | Only `idle` accepts new messages (FR-005) |
| `rejected_draft` | text or nothing | Over-limit text kept for editing; cleared on send or discard (FR-006) |

```text
idle --message accepted--> waiting --reply or failure--> idle
```

Starting a new conversation replaces the object, so it is available only in `idle`.

### Turn

| Field | Type | Rules |
|---|---|---|
| `message` | text | 1 to 2,000 characters after trimming (FR-006) |
| `answer` | text | Secrets removed, or the friendly failure text |
| `outcome` | `ok`, `failed` or `timed_out` | Set by the chat |
| `elapsed_ms` | number | Measured by the chat |
| `details` | sanitized ReplyDetails or nothing | Stored only in troubleshooting mode (FR-016) |
| `details_state` | `complete`, `incomplete` or `unavailable` | Shown in the view (FR-015) |

Failed and timed-out turns get details built by the chat, with the sanitized error, so every reply has
details in troubleshooting mode (SC-004).

## Sanitization

Details are stored only after passing through the sanitizer, so views can only see safe
values. Secrets are removed from answers and from details, including errors and dictionary keys. See
[research.md](research.md), section 8.
