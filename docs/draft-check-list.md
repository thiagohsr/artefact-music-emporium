# Draft Check List

A basic check list to help me evolve each topic and track progress of the main concerns.

## Done

- [x] Build the seed database with sample data (products, orders, customers, etc.) and make it easy to reset to the initial state
- [x] Script to create the SQLite database and populate it with sample data
- [x] Use Streamlit for the interface, with a troubleshooting mode to show how each reply was produced
- [x] Decide the base deps: streamlit, uv, pytest
- [x] Script to create the embeddings for the policies (`make policy-index`), plus a draft agent to help regression testing in the local `draft/policy-agent` branch

## In review

- [ ] Merge the policy index (PR #5)

## Next: agent spec

- [ ] Decide the agent framework: Pydantic AI or LangGraph
- [ ] Define the tools for the agent to use: products, orders and order status, payment terms, policy lookup
- [ ] Reason about a secure way to handle the tool calling interactions with the database
- [ ] Define the agent loop: receive message, decide which tool to use, call the tool, return the answer
- [ ] Exception handling and logging (`docs/pending-updates.md`)
- [ ] Improvements found in code review, to tackle with the real agent (`docs/pending-updates.md`)

## After that: evaluation

- [ ] Define the evaluation plan: how to test the agent, what questions to ask, how to check if the answer is correct, right source is used, etc. (score the answer maybe?)
- [ ] Define guardrails to avoid hallucinations and out-of-scope answers (e.g. "if the question is not about the store, politely decline and redirect to what it can help with")

## Delivery (required by the brief)

- [ ] 3 to 5 example conversations from real agent runs, at least one non-trivial
- [ ] README: justify the framework, model, retrieval architecture and prompt strategy
- [ ] README: what I would do with more time
- [ ] README: how AI coding assistants were used
- [ ] Deploy from `release/streamlit-version` to Streamlit's free hosting

## Deferred

- [ ] Router and specialist subagents: documented as the next step in the README, split only if the evaluation shows it's needed
- [ ] Figure out if we can make it easy to move to a production ready database (e.g., Postgres) and what would be the implications
- [ ] Caching, for the "with more time" section of the README: order the prompt with the static part first so the provider's prompt caching applies; cache question embeddings for `policy_lookup` by exact text; and, only after measuring real timings on OpenRouter, consider caching answers that depend on the manual alone, never ones with prices, stock, promotions or orders (manual 7.1, Principle I)
- [ ] Define memory history based on identified users
- [ ] Phase two: derive the system user ID with a secret-keyed hash of phone and email instead of a mapping table, so stored conversations can't be linked to a customer without the key
- [ ] FastAPI or FastMCP for a second phase, if we find time to deploy API and frontend
