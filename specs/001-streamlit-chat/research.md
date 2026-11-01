# Research: Customer Chat with Troubleshooting View

Behavior marked **verified** was tested against Streamlit 1.66.1 on Python 3.13 on 2026-11-01. There are
no open clarifications.

## 1. Safe Streamlit configuration

**Decision**: Commit `.streamlit/config.toml` with `browser.gatherUsageStats = false`,
`client.showErrorDetails = "none"`, `client.toolbarMode = "minimal"` and
`server.address = "localhost"`. `make run-dev` overrides `client.showErrorDetails` to `"full"`, so crash
details appear in the browser only in troubleshooting mode.

**Rationale**: The defaults conflict with the spec. Streamlit shows full error details in the browser
(FR-016), sends usage statistics, and sets no bind address, while the prototype has no login. Binding
to localhost and hiding errors were verified on a running server.

**Alternatives considered**: Command-line flags in the Makefile, which would not protect anyone running
`streamlit` directly.

## 2. Displaying message text

**Decision**: Render messages with `st.text`, not `st.markdown`, and never enable unsafe HTML.

**Rationale**: FR-021 requires plain content. **Verified** that `st.text` keeps `**bold**`, `<b>` tags
and links as literal text.

**Alternatives considered**: Escaping and using Markdown, which would allow richer replies but gives
messages from customers and tools a way to affect the page. This can be revisited if the real agent
needs lists or emphasis.

## 3. Chat flow and blocking new messages

**Decision**: Use two passes. The first adds the message and reruns with the input disabled and a
spinner visible. The second calls the agent, stores the result and reruns with the input enabled.

**Rationale**: Streamlit reruns the whole script on each interaction, so the input must already be
disabled before the agent call begins (FR-005). `st.chat_input` has a `disabled` option, and `AppTest`
**verified** driving it.

## 4. Message length limit

**Decision**: Do not set `max_chars` on the input. Validate after submit, and when a trimmed message is
over 2,000 characters, do not call the agent. Show an error in Portuguese with the message's length and
the limit, and an edit panel containing the full text, with buttons to send and discard.

**Rationale**: Validation tells the person exactly what happened and never cuts their text silently. It
keeps the normal chat input for ordinary messages, and `st.chat_input` cannot refill its own text after
a submit, so the panel is what keeps the text editable. **Verified** in `AppTest`: rejection with the
full text kept, a second rejection after a still-long edit, a successful send after shortening,
acceptance at exactly 2,000 characters, discard, and sending a new message while the panel is open.

**Limitation**: Streamlit sends text to the app only on submit, so the count cannot update while the
person types in the chat input.

**Alternatives considered**: `max_chars` on the input, which limits what can be entered but gives no
Portuguese message, and its handling of pasted text could not be verified without a browser. A text
area and button for all messages, which would give up the normal chat experience to serve a rare case.

## 5. Reply time limit

**Decision**: Run each agent call in a daemon thread and wait up to 60 seconds. On timeout, show the
failure message and discard any late result. The limit can be overridden by a setting so tests stay
fast.

**Rationale**: **Verified** that `Future.cancel()` cannot stop a running call, so the call cannot be
interrupted. A daemon thread does not block application shutdown, unlike a thread pool worker.

**Limitation**: A timed-out call keeps running until it ends. The real agent should set timeouts on its
own model and tool calls.

## 6. Troubleshooting view layout

**Decision**: Show one collapsed expander under each reply, containing a summary and a nested expander
per step. If the details exceed 10 steps or 6,000 sanitized characters, the expander shows the summary
and a button that opens a large `st.dialog`, with one expander per part. Values over 2,000 characters
are shortened inline with a marker, and the modal shows the full sanitized value.

**Rationale**: This is the layout the project owner chose. **Verified** in `AppTest` that nested
expanders and expanders inside a dialog run without error. The thresholds are starting values. Rendering
in a real browser is a manual check.

## 7. Reply details format

**Decision**: Use standard-library frozen dataclasses with a generic list of steps. Each step has a kind
(`tool`, `retrieval`, `model` or `reasoning`) and JSON-compatible inputs and results.

**Rationale**: The format has to accept output from LangGraph or Pydantic AI, because that choice belongs
to the agent spec. Each framework would map its own events to steps through a small adapter, so neither
one is favored or needed here.

**Alternatives considered**: Pydantic models, which would add a dependency this feature does not need.
Framework event types, which would tie the chat to a framework.

## 8. Removing secrets

**Decision**: Sanitize once, in the chat layer, as soon as the agent returns and before anything is
stored in session state, for replies and details alike. With troubleshooting mode off, details are
discarded and never stored. Replace known formats (API keys, tokens, JWTs, private keys, bearer values)
and every value from `.env` and sensitive-looking environment variables, except model names and very
short values.

**Rationale**: One entry point means no view can skip it, and it also covers exception text.

**Limitation**: Pattern matching can miss unusual secret formats.

## 9. Selecting the agent and turning on troubleshooting

**Decision**: Use `EMPORIO_AGENT` (`stand_in` by default for now) and `EMPORIO_TROUBLESHOOTING` (off by
default), read once at startup. Selecting an agent that is unknown or cannot start shows an error page
naming the setting.

**Rationale**: These settings cannot be changed from the page (FR-013), and there is no silent switch to
the stand-in (FR-012). The default changes to the real agent in its own spec.

## 10. Dependencies and packaging

**Decision**: Add `streamlit>=1.66,<2` and `python-dotenv>=1,<2`, and `pytest>=9,<10` to the dev group.
Use setuptools to build the `src/emporio` package, as required by the developer.

**Rationale**: Streamlit is the chosen interface. It is a heavy install, including pandas and pyarrow, but
that is acceptable for this prototype, and the agent package stays free of it. The exact versions are
pinned by `uv.lock`. The `src/` layout needs a build system, because without one uv installs only the
dependencies and `import emporio` fails, even with `__init__.py` in place. A `[tool.setuptools]` section
alone does not fix this. **Verified** with uv 0.6.12 that a `[build-system]` section using setuptools
makes the import work, finds `src/emporio` with no other settings and is not installed in `.venv`.

**Limitation**: Setuptools generates an `.egg-info` folder in `src/`, so `.gitignore` must exclude it.

**Alternatives considered**: Hatchling, which also works and generates no folder, but needs a `packages`
setting because the project and package names differ, and offers nothing else this project needs.
