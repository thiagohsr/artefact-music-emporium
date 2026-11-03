# Decisions and Limitations

The assumptions, technical decisions and known limitations behind the agent.

## Assumptions

The store manual contradicts itself on the WhatsApp number, the email address and the credit card
installment minimums. The rules the agent follows, and the questions still open with the store, are
in [Stakeholder Clarifications](stakeholder-clarifications.md). Issues in the store data are in
[Store Data Corner Cases](corner-cases/store-data.md).

## Decisions

- **One agent with typed tools:** Pydantic AI runs a plain tool loop over eight tools. Choosing the source is the brief's
  core requirement, and in a loop a wrong first call is cheap, because the model reads the result and tries another. A
  router with specialist agents is the documented next step if the evaluation shows the model picking the wrong tools,
  following [OpenAI's guidance](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
  to maximize a single agent first, and [Anthropic's](https://www.anthropic.com/engineering/building-effective-agents) to add
  complexity only when needed.
- **Tools hold what must be exact:** lookups, payment math, the identity check and writes are plain Python, so they're
  tested without a model. Real runs shaped them: `installments` is required because the model omitted it, and a successful
  order check includes the open conversation because `qwen3:8b` called that tool in only 1 of 5 runs.
- **Model and provider:** `qwen3:8b` on a self-hosted Ollama server first, and OpenRouter as the fallback, which is also what
  an evaluator without access to the server uses. Thinking stays on: in one test, turning it off halved the time but
  the reply stated a made-up price.
- **Prompt strategy:** section 7 of the manual is read from the policy index into the instructions, so the store's own tone,
  flow and special situations drive the agent. Around it are the rules that resolve the manual's contradictions, and the
  computed date and business hours, so the model doesn't work them out.
- **Conversation history:** conversations last for the session. Only customers who pass the order check get theirs stored,
  in SQLite, held by a random user ID with names, phones and emails masked, so they can continue after a page reload.
- **Exceptions:** a broad `except` stays only at real boundaries, logged, with its reason. Failures go to the terminal
  with secrets removed, and customers only see the friendly message.
- **Streamlit, called directly:** the chat calls the agent in the same process, with no API layer. This
  keeps the prototype to one command while the focus is on the agent and its evaluation. The agent
  doesn't depend on Streamlit, so it can be called from a script or test.
- **One small agent interface:** the chat only knows `respond(conversation_id, message)`. Reply details
  are plain dataclasses with a generic list of steps, so they don't tie the chat to an agent framework.
- **Stand-in agent:** it tests the chat and its failure paths with no model or store data. It's never used silently: the
  page shows a notice, and an agent that fails to start shows an error instead of falling back to it.
- **Markdown for replies, plain text for customers:** replies use `st.markdown`, because the models write lists and bold
  that are hard to read as plain text. `$` is escaped so that prices aren't read as math. Customer messages stay in `st.text`, so
  what a customer types can't change the page.
- **Secrets removed in one place:** replies and details pass through the sanitizer as soon as the agent
  returns, before anything is stored, so no view can skip it. With troubleshooting off, details are
  discarded and never stored.
- **Long messages:** they're validated after sending rather than with a character limit on the input.
  This tells the person what happened in Portuguese and never cuts their text silently.
- **Troubleshooting off by default:** it can only be turned on in the startup settings, never from the
  page.
- **Policy index committed to the repo:** `data/policies.sqlite` holds the manual split into its 28 numbered
  sections, with vectors and keyword search, so nobody needs an embedding provider to get it. Sections 7 and
  10 are instructions for staff, so customer searches skip them. It uses `qwen3-embedding:4b`, the smallest
  model available on both the local Ollama server and OpenRouter, and vectors from one work with questions
  embedded on the other. On 16 gold questions, the right section is in the top 3 for all 16 and first for 12,
  on both providers. Keyword search alone gets 15 of 16 in the top 3, and misses "Me arrependi da minha
  compra".
- **Setuptools as the build backend:** the `src/` layout needs a build system, or `import emporio` fails.
  Setuptools finds the package with no extra settings.

## Known Limitations

- **Model reliability:** on `make agent-check`, three full runs scored 20, 22 and 21 of 22 on `qwen3:8b`, and 22, 21 and 21
  on `gpt-4o-mini`. The misses vary, and include claiming a complaint was registered without calling the tool, and reading
  the order date as the delivery date. No order was shared with wrong or missing details in any run. These are small samples.
- **Guardrails are incomplete:** requests beyond accessories that are off-topic, and attempts to override the instructions,
  aren't handled yet. An earlier draft agent failed such a test, and this one hasn't been hardened against it.
- **Markdown in replies:** links and images in a reply render, and HTML doesn't. A model led into writing an image link would make
  the browser request that address. This hasn't been tested, and nothing filters it.
- **Stored conversations:** masking can miss unusual formats and other people's names. The user ID is pseudonymous, because a
  table in the same file maps it to the customer. Nothing deletes stored conversations, although manual section 9 lets
  customers ask for that. A different customer verifying in the middle of a session closes the first conversation and clears
  its history, but the model call that made the check already had that history, because the switch isn't known until the
  check returns.
- **Order check:** nothing limits repeated guesses at an order's phone and email.
- **Return periods** count from the delivery estimate, because the data has no actual delivery date.
- **Complaints** are recorded, but the store's team has no screen to read them.
- **After closing:** when the agent finishes a conversation, the old messages stay on screen, and the next message starts fresh.
- **Business hours** don't cover holidays, because the manual doesn't list them.
- **Interface:** the chat runs in one process and is meant for local use and small demos. There's no
  login, so it binds to localhost. A real integration would need a separate API.
- **Page reload:** it ends the session, and a customer who wasn't verified loses that conversation.
- **Secret removal only knows configured values:** it removes values from `.env` and sensitive
  environment variables, and anything under a sensitive key name. Another secret in free text, such as a
  third-party token in a tool's error message, isn't caught.
- **Message length:** there's no live character count, and an over-limit message is only rejected after
  sending. Streamlit's `max_chars` would add a live count, but it silently drops a paste over the limit, so
  the chat keeps the edit panel instead.
- **Troubleshooting view:** it shows customer data unmasked, because the data is fictional and the mode is
  for local use. Real customer data would require masking or restricted access.
- **Crash details:** `make run` hides application crash details from the browser, and `make run-dev`
  shows them in full to make debugging easier. Streamlit displays these details itself, so they skip
  the step that removes secrets. A secret in a crash message could appear on screen in `make run-dev`,
  so review any screenshot of a crash before sharing it.
