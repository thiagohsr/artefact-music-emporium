# Draft Check List

## This document is a basic check list to help me evolve each topic and track progress of the main concerns

- Use streamlit to create the interface and save time on the front-end development. Consider to enable a reasoning mode to show the reasoning and help the troubleshooting.

- Decide python deps: streamlit, langgraph and pydantic (or pydanticAI), uv, pytest, (fastapi or fastMCP for second phase if we find time to deploy API and Frontend)

- Script to create the sqlitedatabase and populate it with sample data
- Script to create the embeddings for the policies and store info
- Define the evaluation plan: how to test the agent, what questions to ask, how to check if the answer is correct, right source is used, etc. (score the answer maybe?)

- Define tools for the agent to use: SQL tool, policy lookup tool, delivery, orders, order status, etc.
- Reason about a secure way to handle the tool calling interactions with the database.
- Figure out if we can make it easy to move to a production ready database (e.g., Postgres) and what would be the implications of that.

- Define main orchestrator agent loop: receive message, decide which tool to use, call tool, return answer  (should we consider subagents for each tool?).

- Retrieval cache for more static data (e.g., policies, store info) to avoid repeated retrievals.

- Define memory history based on identified users

- Define guardrails for the agent to avoid hallucinations and out-of-scope answers (e.g. "if the question is not about the store, politely decline and redirect to what it can help with").
