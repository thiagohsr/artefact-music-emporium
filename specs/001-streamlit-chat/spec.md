# Feature Specification: Customer Chat with Troubleshooting View

**Feature Branch**: `001-streamlit-chat`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Streamlit chat interface for the Empório da Música customer service agent, plus a development mechanism to troubleshoot chat <> agent interactions. Scope: Streamlit setup and how it is run; a chat where a person sends text messages and sees replies, with conversation kept during the session; a developer/troubleshooting view that shows how each reply was produced (tool calls and their inputs/outputs, sources used, model and provider, timing, errors), off by default for customers. Streamlit calls the agent directly with no API layer; FastAPI and MCP are out of scope. The agent itself (tools, retrieval, persona rules) is a separate spec, so this feature depends only on a small agent interface such as respond(session_id, message) returning the answer plus trace data, which must not import Streamlit, and can be exercised with a stand-in agent until the real one exists. The troubleshooting view must not expose secrets, and customer personal data handling must respect the constitution's privacy principle."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat with the store's assistant (Priority: P1)

A customer opens the chat, types a message in Portuguese and reads the reply. They can continue the conversation, and earlier messages stay visible, so the exchange feels like a normal text conversation with the store.

**Why this priority**: A text conversation is the core deliverable of the challenge. Everything else in this feature supports it.

**Independent Test**: Start the application with the stand-in agent, exchange several messages, and confirm that each reply appears under its message, in order, with the earlier messages still visible.

**Acceptance Scenarios**:

1. **Given** the chat is open, **When** the person sends a message, **Then** the message appears immediately and a progress indicator shows until the reply appears.
2. **Given** a conversation with earlier messages, **When** the person sends another message, **Then** all earlier messages remain visible in order and the agent receives the same conversation identifier as before.
3. **Given** a conversation is in progress, **When** the person starts a new conversation, **Then** the messages are cleared and the agent receives a new conversation identifier.
4. **Given** two people use the chat in separate browser sessions, **When** both send messages, **Then** neither can see the other's messages.
5. **Given** the agent fails while answering, **When** the failure occurs, **Then** the person sees a friendly message in Portuguese with the store's contact channels, can keep using the chat, and sees no internal error details.

---

### User Story 2 - See how each reply was produced (Priority: P2)

A developer runs the application in troubleshooting mode and inspects each reply: which tools ran, with what inputs and results, which sources were used, which model and provider answered, how long each step took, and what failed. This shows why the agent answered as it did, without reading logs.

**Why this priority**: The constitution requires that source routing can be observed, and this view makes it possible to diagnose wrong answers while the agent is built. The chat is still usable without it.

**Independent Test**: Start the application in troubleshooting mode with the stand-in agent, send a message that triggers a simulated tool call and another that triggers a simulated failure, and confirm that both replies have complete details. Then start it in normal mode and confirm that the details are not available.

**Acceptance Scenarios**:

1. **Given** troubleshooting mode is on, **When** a reply appears, **Then** the developer can open its details, attached to that reply, and see each step in order with its inputs, results and duration.
2. **Given** troubleshooting mode is on, **When** a reply is produced, **Then** the details show the sources used, the model and provider that answered, the total time, and whether a fallback provider was used.
3. **Given** troubleshooting mode is on, **When** a step fails, **Then** the details show which step failed and a description of the error, along with any steps completed before it.
4. **Given** a reply used no tools or sources, **When** the developer opens its details, **Then** the details say so explicitly, so it cannot be mistaken for missing data.
5. **Given** troubleshooting mode is off, **When** anyone uses the chat, **Then** no internal details are shown and nothing in the page can turn them on.
6. **Given** a result or error includes secrets, **When** it appears in the details, **Then** the secrets are never shown.

---

### User Story 3 - Start the application with one command (Priority: P3)

A developer or evaluator follows the README and starts the application with one command, in normal or troubleshooting mode. It works before the real agent exists, because a clearly labelled stand-in agent is available.

**Why this priority**: The constitution requires that an evaluator can run the project from the README alone, and a stand-in lets this feature be built and tested independently of the agent. It ranks below the chat and the details because it supports them rather than being the experience itself.

**Independent Test**: On a clean checkout, follow the README to set up and start the application, confirm the chat opens and answers using the stand-in agent, and then repeat in troubleshooting mode.

**Acceptance Scenarios**:

1. **Given** the project's environment is set up, **When** the developer runs the documented command, **Then** the chat opens and is ready to use.
2. **Given** the stand-in agent is in use, **When** the chat is shown, **Then** a visible notice says that replies are simulated.
3. **Given** the real agent is selected but cannot start, for example because its configuration is missing, **When** the application starts, **Then** it shows which setting is missing, without revealing any secret values, and does not silently switch to the stand-in.

---

### Edge Cases

- **Empty message**: messages that are empty or contain only spaces are not sent, and the agent is not called.
- **Very long message**: messages over 2,000 characters are not sent, and the person is told the limit in Portuguese with their text kept for editing.
- **Sending during a reply**: a person cannot send another message until the current reply finishes, so messages cannot arrive out of order.
- **Slow reply**: if the agent takes more than 60 seconds, the attempt ends with the same friendly failure message, and the details record a timeout.
- **Page refresh or closed browser**: the conversation ends and starts empty next time. This is expected behavior for this feature.
- **Incomplete details from the agent**: a reply with missing or malformed details is still shown to the person, and the view marks the details as unavailable or incomplete.
- **Very large tool results**: long results are shortened in the view, with an indication that they were shortened and a way to see the full content.
- **Text from people or tools containing formatting or instructions**: it is displayed as plain content and cannot change the page or reveal hidden details.

## Requirements *(mandatory)*

### Functional Requirements

#### Chat

- **FR-001**: System MUST let a person send text messages and show the agent's replies in chronological order.
- **FR-002**: System MUST keep the conversation visible and available to the agent for as long as the browser session lasts.
- **FR-003**: System MUST identify each conversation with a unique identifier and keep conversations in separate browser sessions isolated from each other.
- **FR-004**: Users MUST be able to start a new conversation, which clears the visible messages and creates a new identifier.
- **FR-005**: System MUST show progress while waiting for a reply and block new messages until the reply finishes.
- **FR-006**: System MUST reject empty messages and messages over 2,000 characters without calling the agent, keeping any rejected text for editing.
- **FR-007**: All customer-facing text in the chat MUST be in Brazilian Portuguese and match the store's informal but professional tone.
- **FR-008**: When the agent fails or takes more than 60 seconds, System MUST show a friendly message with the store's contact channels, reveal no internal details in the chat, and keep the chat usable.

#### Agent interface

- **FR-009**: System MUST interact with the agent only through one defined interface that receives a conversation identifier and a message, and returns the reply and its details.
- **FR-010**: The agent MUST be usable through this interface without the chat interface running, so the evaluation can call the same agent the chat uses.
- **FR-011**: System MUST include a stand-in agent that follows the same interface and can simulate replies, tool calls, source use, a fallback and failures, so that this feature can be tested without a model or store data.
- **FR-012**: System MUST show a visible notice whenever the stand-in agent is in use, and MUST NOT silently replace a real agent that failed to start.

#### Troubleshooting view

- **FR-013**: Troubleshooting mode MUST be off by default and can be turned on only in the application's startup configuration, never from within the page.
- **FR-014**: When troubleshooting mode is on, System MUST attach to each reply its details: the steps in order with inputs, results, duration and status; the sources used; the model and provider; whether a fallback was used; the total time; and any errors.
- **FR-015**: System MUST state explicitly when a reply used no tools or sources, and when its details are missing or incomplete.
- **FR-016**: When troubleshooting mode is off, System MUST NOT include any internal details in the page.
- **FR-017**: System MUST never show secrets in the chat or the details. These include API keys, access credentials and values from the project's private configuration.
- **FR-018**: System MUST NOT save conversations or details to disk.

#### Running the application

- **FR-019**: System MUST start with one documented command, with a documented way to turn on troubleshooting mode and to choose the stand-in or the real agent.
- **FR-020**: When the selected agent cannot start, System MUST show which setting is missing or invalid, without revealing any values.
- **FR-021**: System MUST treat text from people, tools and the agent as plain content, so it cannot alter the page or reveal hidden details.

### Key Entities

- **Conversation**: one exchange between a person and the agent in a browser session. It has a unique identifier and an ordered list of messages, and it lasts until the session ends or a new conversation starts.
- **Message**: a single piece of text from the person or the agent, in its place in the conversation. A message from the agent links to its reply details.
- **Reply details**: how one reply was produced. They include the steps, sources used, model and provider, fallback use, total time, errors and completeness.
- **Step**: one action taken while producing a reply, such as a tool call. It has a name, inputs, result, duration and status.
- **Agent**: whatever fulfils the agent interface. It is either the stand-in or the real agent from a later specification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can start the application from the README in under 2 minutes after the environment is set up.
- **SC-002**: With the stand-in agent, a person can complete a 20-message conversation with every message and reply visible, in order.
- **SC-003**: Progress appears within 1 second of sending a message.
- **SC-004**: In troubleshooting mode, 100% of replies have details available, including replies that failed.
- **SC-005**: Using the details alone, a developer can identify the tools, sources, model and failing step for a reply in under 30 seconds.
- **SC-006**: In a test with planted secrets in tool results and errors, 0 secrets appear in the chat or the details.
- **SC-007**: With troubleshooting mode off, 0 internal details appear in the page across the test conversations, including during failures.
- **SC-008**: The agent interface can be exercised by an automated check with the chat interface not running.
- **SC-009**: In a test with two simultaneous sessions, neither session shows or receives the other's messages.

## Assumptions

- **Chosen interface**: Streamlit was chosen by the project owner, and it calls the agent directly in the same application. Separate backend services, FastAPI and MCP are out of scope and may be considered in a later phase.
- **The real agent is separate**: tools, retrieval, persona rules, identity verification and model selection belong to a later specification. This feature uses the stand-in agent and defines the interface the real one must follow.
- **Conversation memory**: a conversation lasts for the browser session. History across sessions is out of scope for this feature.
- **Access**: this is a prototype without logins, so troubleshooting mode is protected only by being set in the startup configuration. A public deployment would keep it off.
- **Developer-facing language**: the troubleshooting view may be in English. Only customer-facing text must be in Brazilian Portuguese.
- **Limits**: the 2,000-character message limit and 60-second reply limit are reasonable defaults for a text support chat, and can be revisited during evaluation.
- **Single-user scale**: the prototype runs for local use and small demos, not for high numbers of simultaneous users.
- **Example conversations**: the brief's example conversations must come from the real agent, per the constitution, so replies from the stand-in agent do not qualify.
