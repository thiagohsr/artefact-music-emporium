# Technical Decisions and Limitations

Why the agent is built the way it is, what was assumed, and where it falls short.

**Contents:** [Assumptions](#assumptions) · [The agent](#the-agent) · [Retrieval](#retrieval) · [Conversations](#conversations) · [The chat](#the-chat) · [Reliability and safety](#reliability-and-safety) · [Project setup](#project-setup) · [Known limitations](#known-limitations) · [Designed but not built](#designed-but-not-built)

## Assumptions

The store manual contradicts itself on the WhatsApp number, the email address and the credit card installment minimums.

- [Stakeholder Clarifications](stakeholder-clarifications.md) has the rules the agent follows and the questions still open with the store.
- [Store Data Corner Cases](corner-cases/store-data.md) has the issues found in the store data.

## The agent

### One agent with typed tools

Pydantic AI runs a plain tool loop over eight tools.

- **Why:** choosing the right source is the brief's core requirement, and in a loop a wrong first call is cheap, because the model reads the result and tries another.
- **Next step:** a router with specialist agents, if the evaluation shows the model picking the wrong tools.
- **Sources:** [OpenAI](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) advises maximizing a single agent first, and [Anthropic](https://www.anthropic.com/engineering/building-effective-agents) advises adding complexity only when needed.

### Tools hold what must be exact

Lookups, payment math, the identity check and writes are plain Python, so they're tested without a model. Real runs shaped them:

- `installments` is required, because the model omitted it.
- A successful order check includes the open conversation, because `qwen3:8b` called that tool in only 1 of 5 runs.
- Orders are found only by tracking code, because order IDs are sequential and easy to guess. Phone and email are required as well.

### Model and provider

`qwen3:8b` on a self-hosted Ollama server comes first, with OpenRouter as the fallback. OpenRouter is also what an evaluator without access to the server uses.

Thinking stays on: in one test, turning it off halved the time, but the reply stated a made-up price.

### Prompt strategy

Section 7 of the manual is read from the policy index into the instructions, so the store's own tone, flow and special situations drive the agent. Around it are:

- the rules that resolve the manual's contradictions
- the computed date and business hours, so the model doesn't work them out

## Retrieval

`data/policies.sqlite` is committed to the repo, so nobody needs an embedding provider to get it. It holds the manual split into its 28 numbered sections, with vectors and keyword search.

- **Staff sections:** sections 7 and 10 are instructions for staff, so customer searches skip them.
- **Embedding model:** `qwen3-embedding:4b`, the smallest available on both the local Ollama server and OpenRouter. Vectors from one work with questions embedded on the other.

| Measured on 16 gold questions | In the top 3 | First |
|---|---|---|
| Vector search, on both providers | 16 of 16 | 12 of 16 |
| Keyword search alone | 15 of 16 | not recorded |

Keyword search is only the fallback: it misses "Me arrependi da minha compra".

## Conversations

| Situation | What happens |
|---|---|
| Page reload | The conversation comes back, for up to 30 minutes after the last message, through a link in the page's address |
| Customer who passed the order check | The conversation is also stored in SQLite, held by a random user ID with names, phones and emails masked. They can continue it from a new tab by verifying again |
| Anyone else, without the link | The conversation is lost |
| "Nova conversa" | Ends the conversation, and its link stops working |

**Why a link for reloads:** an accidental reload is what costs a customer a large quote, and this fixes it with nothing asked of them and no new identity to protect. An unknown link always starts a new conversation under a new ID.

## The chat

| Decision | Why |
|---|---|
| **Streamlit, called directly, with no API layer** | Keeps the prototype to one command while the focus is on the agent. The agent doesn't depend on Streamlit, so a script or test can call it |
| **One small agent interface** | The chat only knows `respond(conversation_id, message)`. Reply details are plain dataclasses with a generic list of steps, so nothing ties the chat to a framework |
| **Stand-in agent** | Tests the chat and its failure paths with no model or store data. It's never used silently: the page shows a notice, and an agent that fails to start shows an error instead of falling back to it |
| **Markdown for replies, plain text for customers** | The models write lists and bold, which are hard to read as plain text. `$` is escaped so prices aren't read as math. Customer messages stay in `st.text`, so what a customer types can't change the page |
| **Long messages checked after sending** | Tells the person what happened in Portuguese, and never cuts their text silently |
| **Troubleshooting off by default** | It can only be turned on in the startup settings, never from the page |

## Reliability and safety

| Decision | Why |
|---|---|
| **Secrets removed in one place** | Replies and details pass through the sanitizer as soon as the agent returns, before anything is stored, so no view can skip it. With troubleshooting off, details are discarded and never stored |
| **Exceptions handled at boundaries** | A broad `except` stays only at real boundaries, logged, with its reason. Failures go to the terminal with secrets removed, and customers only see the friendly message |

## Project setup

**Setuptools as the build backend:** the `src/` layout needs a build system, or `import emporio` fails. Setuptools finds the package with no extra settings.

## Known limitations

### The model

| Limitation | Detail |
|---|---|
| **Reliability varies** | Three full runs of `make agent-check` scored 20, 22 and 21 of 22 on `qwen3:8b`, and 22, 21 and 21 on `gpt-4o-mini`. No order was shared with wrong or missing details in any run. These are small samples, measured before the latest fixes |
| **Guardrails are incomplete** | Off-topic requests beyond accessories, and attempts to override the instructions, aren't handled yet. An earlier draft agent failed such a test, and this one hasn't been hardened against it |
| **Links and images in replies** | They render, and HTML doesn't. A model led into writing an image link would make the browser request that address. This hasn't been tested, and nothing filters it |

### Customer data

| Limitation | Detail |
|---|---|
| **The page link opens the conversation** | Anyone with the link can read it for up to 30 minutes after the last message, including order details a verified customer already saw. This matters on a shared computer, because the link stays in the browser's history |
| **Masking** | It can miss unusual formats and other people's names |
| **Pseudonymous user ID** | A table in the same file maps it to the customer |
| **No deletion** | Nothing deletes stored conversations, although manual section 9 lets customers ask for that |
| **Customer switch** | A different customer verifying mid-session closes the first conversation and clears its history. The model call that made the check already had that history, because the switch isn't known until the check returns |
| **Order check guesses** | Nothing limits repeated guesses at an order's phone and email |
| **Troubleshooting view** | It shows customer data unmasked, because the data is fictional and the mode is for local use. Real data would need masking or restricted access |

### Store rules

| Limitation | Detail |
|---|---|
| **Orders with no tracking code** | Only the tracking code finds an order, and it's sent when the order is dispatched. So the agent can't look up pending, confirmed or cancelled orders, which is 12 of the 20 in the data, and points those customers to the store's channels |
| **Return periods** | They count from the delivery estimate, because the data has no actual delivery date |
| **Business hours** | They don't cover holidays, because the manual doesn't list them |
| **Complaints** | They're recorded, but the store's team has no screen to read them |

### The chat

| Limitation | Detail |
|---|---|
| **Closed tab or another device** | A customer who doesn't keep the link and didn't pass the order check loses the conversation. See [Designed but not built](#designed-but-not-built) |
| **Two tabs on one link** | Both show the same conversation, and they don't refresh each other |
| **After closing** | When the agent finishes a conversation, the old messages stay on screen, and the next message starts fresh |
| **One process** | Meant for local use and small demos. There's no login, so it binds to localhost, and a server restart loses unverified conversations. A real integration would need a separate API |
| **Message length** | There's no live character count, and an over-limit message is only rejected after sending. Streamlit's `max_chars` would add a count, but it silently drops a paste over the limit, so the chat keeps the edit panel instead |

### Secrets

| Limitation | Detail |
|---|---|
| **Only known values are removed** | The sanitizer removes values from `.env` and sensitive environment variables, and anything under a sensitive key name. Another secret in free text, such as a third-party token in a tool's error message, isn't caught |
| **Crash details** | `make run` hides them from the browser, and `make run-dev` shows them in full for debugging. Streamlit displays them itself, so they skip the sanitizer, and a secret in a crash could appear on screen. Review any screenshot of a crash before sharing it |

## Designed but not built

### Conversation recovery with contact details

**Status:** specified in [spec 003](../specs/003-conversation-recovery/spec.md), not implemented.

**The problem it solves:** a customer who closes the tab, or moves to another device, loses a conversation that never passed the order check.

**The design:** the agent asks for a phone and email when someone asks for a quote, and those same details recover the conversation for 30 minutes. Phone and email aren't secret, so they open only conversations that never passed the order check, and order details always need the tracking code, phone and email.

**Why it isn't built:** the page link fixes the accident that started this, with much less risk. Contact details add a new identity type and changes around the order check, which is the code that protects customer data.
