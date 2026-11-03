# Draft Check List

A basic check list to help me evolve each topic and track progress of the main concerns.

## Done

- [x] Build the seed database with sample data (products, orders, customers, etc.) and make it easy to reset to the initial state
- [x] Script to create the SQLite database and populate it with sample data
- [x] Use Streamlit for the interface, with a troubleshooting mode to show how each reply was produced
- [x] Decide the base deps: streamlit, uv, pytest
- [x] Agent framework: Pydantic AI, with one agent and a tool loop
- [x] Tools for products, orders, payment terms, policies, conversations and complaints, with identity checked in the tool
- [x] Conversations stored by user ID for identified customers, with their data masked
- [x] Exception handling and logging, and the code review improvements
- [x] Script to create the embeddings for the policies (`make policy-index`), plus a draft agent to help regression testing in the local `draft/policy-agent` branch

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
- [ ] Phase two: derive the system user ID with a secret-keyed hash of phone and email instead of a mapping table, so stored conversations can't be linked to a customer without the key
- [ ] FastAPI or FastMCP for a second phase, if we find time to deploy API and frontend
- [ ] Grow the evaluation suite with Pydantic Evals: today `make evals` covers three return cases, and `scripts/check_agent.py` still holds 23 older checks. With more time: port those into `evals/`, add the scope and attack cases, a small judge for tone and persona, hold out part of the cases from prompt tuning, and compare a newer or larger Qwen on the same cases. A first run showed neither model calls `policy_lookup` on a return, which is what the suite should keep measuring
- [ ] Proper test fixtures: tests depend on the store's CSV data, so changing a row breaks unrelated tests (removing customer 43 broke an order privacy test). Each test should create the rows it needs, with the CSVs only covering the seed step
