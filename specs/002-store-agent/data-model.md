# Data Model: Store Customer Service Agent

Existing store tables are read-only. The tables below are new, in `data/emporio.sqlite`. `make db` creates them and
keeps their rows, while `make db-reset` removes them with the rest of the database.

## customer_identities

| Column | Type | Rules |
|---|---|---|
| `user_id` | text, primary key | Random, the system user ID |
| `customer_id` | integer | Unique. No foreign key, because reseeding deletes `customers` rows |

## stored_conversations

| Column | Type | Rules |
|---|---|---|
| `stored_id` | text, primary key | Random |
| `user_id` | text | References `customer_identities` |
| `status` | `open` or `closed` | See the states below |
| `messages` | JSON text | Masked, with no thinking parts |
| `updated_at` | text | UTC time of the last message |

```text
open --Nova conversa, finish_conversation or 30 minutes without a message--> closed
```

A page reload does not change the status. A customer has at most one open conversation: the most recent wins, and
starting another closes the earlier one.

## complaints

| Column | Type | Rules |
|---|---|---|
| `complaint_id` | integer, primary key | |
| `user_id` | text or nothing | Set when the customer is identified |
| `summary` | text | Masked, required |
| `created_at` | text | UTC |

## Session, in memory

Held by the agent per `conversation_id`, and never written to disk as it is.

| Field | Rules |
|---|---|
| `history` | Pydantic AI messages, unmasked, used for the next run |
| `user_id` | Set only by a successful order check |
| `stored_id` | Set once identified |
| `last_message_at` | Older than 30 minutes means the session has closed |
| `closed` | Set by `finish_conversation` or `end_conversation`. The next message starts a fresh session |

If a different customer passes the order check in the same session, the first customer's stored conversation closes,
and the session's history is cleared before continuing, so that the two never mix (FR-015).

## Changes to the existing reply details

The reply format stays as it is, and a run maps to it as follows:

| Run content | Reply details |
|---|---|
| Tool call and its result | `Step(kind="tool")`, or `retrieval` for `policy_lookup` |
| Thinking | `Step(kind="reasoning")` |
| Sections from `policy_lookup` | `Source("policy", "4.1 ...")` |
| Results from product and order tools | `Source("data", "products")` or `Source("data", "orders")` |
| Model that answered | `model` and `provider`, with `fallback_used` true when it isn't the primary |

Thinking is shown only in the troubleshooting view, and passes through the sanitizer like everything else.
