# Contract: Chat Application

What a person running or using the application can rely on.

## Commands

| Command | Result |
|---|---|
| `make run` | Installs locked dependencies and starts the chat with troubleshooting off |
| `make run-dev` | The same, with troubleshooting on and application crash details shown in the browser |
| `make test` | Runs the automated tests |

## Settings

Read once at startup. Documented in `.env.example`.

| Setting | Values | Default | Effect |
|---|---|---|---|
| `EMPORIO_AGENT` | `stand_in` | `stand_in` | Agent to use; the real agent's value is added by its spec |
| `EMPORIO_TROUBLESHOOTING` | `0` or `1` | `0` | Turns the details on |
| `EMPORIO_REPLY_TIMEOUT_SECONDS` | Positive number | `60` | Reply limit, overridden in tests |

An invalid value shows an error page naming the setting, without values from private settings
(FR-020). The chat does not fall back to the stand-in (FR-012).

## Customer-facing text

All in Brazilian Portuguese (FR-007). Exact wording is decided during implementation, with this content:

| Situation | Must say |
|---|---|
| Input placeholder | An invitation to type a message |
| New conversation button | Start a new conversation |
| Waiting | The assistant is preparing a reply |
| Stand-in notice | Replies are simulated and do not come from the real assistant |
| Message over the limit | The message's length and the 2,000-character limit, with an edit panel holding the full text and buttons to send or discard |
| Agent failure or timeout | The assistant could not answer, try again or use WhatsApp (67) 3341-4444 or (67) 3321-4500, or `contato@emporiodamusica.com.br` |

The contact details follow [Stakeholder Clarifications](../../../docs/stakeholder-clarifications.md).

## Troubleshooting view

Shown only when troubleshooting is on. There is no control in the page to turn it on (FR-013).

- **Each reply**: a collapsed section with the model, provider, fallback use, total time, sources and
  details state, plus one expandable part per step.
- **No tools or sources**: says so explicitly.
- **Large details**: over 10 steps or 6,000 characters, the section shows the summary and a button that
  opens a modal with each part expandable.
- **Long values**: over 2,000 characters, they are shortened with a marker, and the modal has the full
  sanitized value.

With troubleshooting off, the page has no details and no error text from the agent
(FR-016).

## Server defaults

`.streamlit/config.toml` binds to localhost, hides error details in the browser, minimizes the toolbar
and turns off usage statistics. See [research.md](../research.md), section 1.
