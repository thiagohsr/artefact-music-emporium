# Contract: Agent Interface

The only way the chat talks to an agent (FR-009). The real agent from a later spec must follow this too.

```python
class Agent(Protocol):
    name: str
    is_simulated: bool

    def respond(self, conversation_id: str, message: str) -> AgentReply: ...
```

The data types are defined in [data-model.md](../data-model.md).

## Rules

1. **No interface dependency**: nothing under `emporio.agent` imports Streamlit, and `respond` can be
   called from a plain script or test (FR-010, SC-008).
2. **Conversation memory**: the chat sends only the new message. The agent keeps any history it needs
   per `conversation_id`, and must never mix conversations.
3. **Concurrency**: one agent instance serves all sessions and may be called from different threads at
   the same time.
4. **Failures**: `respond` may raise any exception. The chat catches it, and the customer sees only the
   friendly message.
5. **Trusted input only**: the chat validates length and blank messages before calling `respond`.

## Stand-in agent

`is_simulated` is `True`, it uses no model or store data, and the same input always gives the same
output. Its `private_values` lists the fake key from `/sensivel`, so the chat removes it. A leading command in the message selects what it simulates (FR-011):

| Message starts with | Simulates |
|---|---|
| anything else | A simple reply with no steps or sources |
| `/ferramenta` | One `tool` step with inputs and a result, and a `data` source |
| `/politica` | One `retrieval` step and a `policy` source |
| `/fallback` | A reply with `fallback_used` set to true |
| `/raciocinio` | A `reasoning` step followed by a reply |
| `/grande` | Enough steps and data to open the modal |
| `/incompleto` | `complete` set to false |
| `/sem-detalhes` | No details at all |
| `/sensivel` | A fake API key in a step result and an error |
| `/erro` | An exception raised during the reply |
| `/lento` | A delay longer than the reply limit |

## Contract tests

- A fresh Python process that imports `emporio.agent` does not load `streamlit`.
- Every stand-in command returns a valid `AgentReply` or does what its row says.
- A call with no chat running returns an answer.
