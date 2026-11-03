# Feature Specification: Conversation Recovery with Contact Details

**Feature Branch**: `feature/003-conversation-recovery`

**Created**: 2026-11-03

**Status**: Not implemented. See `DECISIONS.md` for why

**Input**: User description: "Conversation recovery with contact details for Empório da Música. Confirmed scope: (1) When a customer asks for a quote, or a conversation is becoming substantial, or the customer asks to recover a conversation, the agent asks for their phone and email. (2) Anyone can use this: the phone and email do not have to match a store customer. (3) The conversation is stored from the moment the customer gives their phone and email, including the session's earlier messages, with personal information obfuscated, under an identity for those contact details. Conversations with no contact details stay unsaved. (4) After a page reload, giving the same phone and email recovers the last open conversation; the existing 30-minute limit stays. (5) Contact details never give access to order details, and never recover a conversation that has passed the order check. The order check always needs the order number or tracking code, the phone and the email. (6) If an order check passes during a conversation, the same session continues; from then on that conversation can only be recovered with the order check. If it matches a different person than an earlier order check, it closes like any other customer switch. (7) The agent only says it saved or noted details when a tool actually did it, and when the customer has not been identified, the conversation lookup tells the model that rather than only saying nothing was found. Done means real-model checks of: a quote conversation recovered after a reload, wrong contact details recovering nothing, recovered conversations giving no order details, and no false claim of saving."

This feature amends spec 002. FR-013 and the page reload edge case of `specs/002-store-agent/spec.md` said that a conversation without an order check is never stored and is lost on a reload. Here, a conversation with contact details is stored and can be recovered. Conversations with neither contact details nor an order check keep the old behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover a conversation after a reload (Priority: P1)

A customer working on a large quote gives their phone and email when the agent asks. The page reloads by accident. They give the same phone and email, and the conversation continues where it stopped, without repeating what they had said.

**Why this priority**: This is the loss that started this feature: a customer in the middle of an important purchase loses everything on a reload.

**Independent Test**: Ask for a quote on several instruments, give a phone and email when asked, reload the page, give the same phone and email, and confirm the agent continues the conversation.

**Acceptance Scenarios**:

1. **Given** a customer asks for a quote, **When** the agent answers, **Then** it asks for their phone and email so that the conversation can be recovered.
2. **Given** a conversation that has become substantial, **When** the customer has not given contact details, **Then** the agent asks for their phone and email.
3. **Given** a customer who gives their phone and email, **When** the conversation continues, **Then** it is stored from that moment, including the session's earlier messages, with their personal information obfuscated.
4. **Given** a customer who isn't in the store's customer records, **When** they give a phone and email, **Then** the conversation is stored and can be recovered in the same way.
5. **Given** a stored open conversation, **When** the customer reloads the page and gives the same phone and email within 30 minutes of their last message, **Then** the agent finds the last open conversation and continues it.
6. **Given** a customer who asks to recover a conversation without giving contact details, **When** the agent answers, **Then** it asks for their phone and email.

---

### User Story 2 - Contact details stay limited (Priority: P1)

Phone and email aren't secret, so they recover only a conversation that never passed the order check. Order details always need the tracking code, the phone and the email.

**Why this priority**: Without this limit, anyone who knows a customer's phone and email could read their order details, which breaks the privacy principle.

**Independent Test**: Recover a conversation with contact details, ask about an order on those same details, and confirm the agent still requires the order number or tracking code. Then try wrong details, and try to recover a conversation that passed the order check, and confirm nothing is recovered.

**Acceptance Scenarios**:

1. **Given** a stored conversation, **When** someone gives a different phone or email, **Then** nothing is recovered.
2. **Given** a stored conversation, **When** someone gives only the phone or only the email, **Then** nothing is recovered, and the agent asks for what is missing.
3. **Given** a customer identified by contact details, **When** they ask about an order, **Then** the agent still requires the tracking code, the phone and the email.
4. **Given** a conversation that passed the order check, **When** someone gives only its phone and email, **Then** that conversation is not recovered.
5. **Given** a stored conversation older than 30 minutes since its last message, **When** the customer gives the same phone and email, **Then** nothing is recovered.

---

### User Story 3 - An order check during a conversation (Priority: P2)

A customer with contact details on the conversation asks about an order and passes the order check. They keep talking in the same session, and from then on the conversation is protected like any other that passed the order check.

**Why this priority**: The conversation may now contain order details, so the weaker contact details must stop opening it.

**Independent Test**: Give contact details, pass an order check with the same phone and email, keep talking, reload, confirm the contact details recover nothing, and confirm the order check does.

**Acceptance Scenarios**:

1. **Given** a conversation with contact details, **When** an order check passes for that same person, **Then** the same session continues with its earlier messages.
2. **Given** that conversation after the order check, **When** the page reloads and someone gives only the phone and email, **Then** nothing is recovered.
3. **Given** that conversation after the order check, **When** the page reloads and the order check passes again, **Then** the conversation continues.
4. **Given** an identified conversation, **When** an order check passes for a different person, **Then** the conversation closes as in any other customer switch, and the two never mix.

---

### User Story 4 - The agent is honest about saving (Priority: P1)

The agent only says it saved or noted something when a tool actually did it. When nobody has been identified yet, the agent knows that, and asks for what it needs rather than saying that nothing can be recovered.

**Why this priority**: In a real test, the agent told a customer it had registered their details when nothing was saved, and the customer would have relied on that.

**Independent Test**: Give a phone and email in a way the agent can't act on, and ask to recover a conversation before giving any details, then read the replies for false claims and for what the agent asks.

**Acceptance Scenarios**:

1. **Given** no tool saved anything, **When** the agent replies, **Then** it doesn't say that it saved, registered or noted the customer's details.
2. **Given** a customer who hasn't been identified, **When** the agent looks for an open conversation, **Then** the result says that the customer isn't identified, as distinct from no conversation being found.
3. **Given** that result, **When** the agent replies, **Then** it asks for the phone and email rather than saying the conversation can't be recovered.

### Edge Cases

- A customer declines to give contact details: the conversation continues in the session and isn't stored.
- A customer gives different contact details during an identified conversation: the conversation closes as in a customer switch, and the two never mix.
- An order check passes for someone other than the person whose contact details are on the conversation: it counts as a different person.
- The new conversation button, or the agent finishing the conversation, closes a conversation with contact details, so it can no longer be recovered.
- Contact details match both a stored conversation and an order's customer: they still recover only the conversation that never passed the order check.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST ask for the customer's phone and email when they ask for a quote, when they ask to recover a conversation, and when a conversation has become substantial, meaning they have been working toward a purchase over several messages.
- **FR-002**: Anyone MUST be able to give contact details, whether or not they match a store customer.
- **FR-003**: Once the customer gives a phone and email, the conversation MUST be stored from that moment, including the session's earlier messages, held under a system identity for those details with their personal information obfuscated.
- **FR-004**: Conversations with neither contact details nor a passed order check MUST NOT be stored.
- **FR-005**: The same phone and email MUST recover the last open conversation stored under them, and only if the last message is within 30 minutes. Both values are required.
- **FR-006**: Contact details MUST NOT give access to order details. The order check MUST always require the tracking code, the phone and the email, and being identified by contact details MUST NOT count toward it.
- **FR-007**: Contact details MUST NOT recover a conversation that has passed the order check, from the moment it passes.
- **FR-008**: When an order check passes for the person already identified on the conversation, the same session MUST continue with its earlier messages, and the conversation MUST then be recoverable only by the order check.
- **FR-009**: When an order check passes for a different person, or different contact details are given during an identified conversation, the conversation MUST close and the two MUST NOT mix.
- **FR-010**: The agent MUST NOT say that it saved, registered or noted anything unless a tool did so in that reply or the conversation is already stored.
- **FR-011**: When nobody is identified, the conversation lookup MUST say so, distinct from no conversation being found.
- **FR-012**: Whether a recovery found nothing because the details were wrong or because no conversation exists MUST NOT be distinguishable in the agent's reply.

### Key Entities

- **Contact identity**: a system identity for a phone and email pair, with no link required to a store customer. It can only recover conversations that never passed the order check.
- **Stored conversation**: the existing record from spec 002, now held either under a contact identity or under a customer who passed the order check, with the same open or closed status and the same obfuscation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the real model, a quote conversation is recovered after a reload using the same phone and email, and the agent continues without asking the customer to repeat themselves.
- **SC-002**: On the real model, wrong, partial or expired contact details recover nothing in any run.
- **SC-003**: On the real model, a conversation recovered with contact details gives no order details in any run, and a conversation that passed the order check isn't recovered by contact details in any run.
- **SC-004**: On the real model, no reply claims that details were saved or noted when they weren't.

## Assumptions

- A phone is compared by its digits and an email without regard to case, as in the order check.
- The 30-minute limit, the obfuscation and the ways a conversation closes are those of spec 002.
- Prices and other store facts in a quote come from the existing tools.
