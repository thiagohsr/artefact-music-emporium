# Feature Specification: Store Customer Service Agent

**Feature Branch**: `feature/002-store-agent`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Customer service agent for Empório da Música that replaces the stand-in behind the existing Agent interface. One agent with a plain tool loop and typed tools for products, order status, payment terms and policy lookup. Calculations are done in tools, not by the model. Persona and per-domain guidance in the prompt, with the store's tone. Primary model on the self-hosted server with OpenRouter as fallback. Order access requires the order number plus both the phone and the email on that order. Identified customers have persistent conversations held by system user ID with their information obfuscated; other conversations last for the session. A session ends on the new conversation button or after 30 minutes without a message. Includes the exception handling and code review improvements recorded in docs/pending-updates.md."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Be served in the store's voice and get correct answers (Priority: P1)

A customer talks to the agent the way they would talk to the store's attendants, in the voice and flow set by section 7 of the manual. The agent greets them, works out what they need, looks it up, answers with prices and conditions, and closes the conversation politely once they confirm they need nothing else.

**Why this priority**: Answering in the store's voice from its real data is the agent's purpose and the core of the challenge.

**Independent Test**: Run a full conversation through each step of the flow, then each special situation, and compare the replies with sections 7.1 to 7.3, the store data and the manual.

**Acceptance Scenarios**:

*Tone (section 7.1)*

1. **Given** any reply, **When** a customer reads it, **Then** it is in Brazilian Portuguese and informal but professional, like a friend who understands music, and avoids overly formal or robotic language.

*Service flow (section 7.2)*

2. **Given** a new conversation, **When** the customer greets the agent, **Then** the agent greets them back, by name if known, and asks how it can help, without consulting any source.
3. **Given** a message that doesn't make the need clear, **When** the agent reads it, **Then** it asks what the customer needs: a product, a question, order tracking or a complaint.
4. **Given** a clear need, **When** the agent answers, **Then** it has first consulted the right tool, and presents the options clearly and objectively, with prices and conditions.
5. **Given** an answered question, **When** the agent finishes answering, **Then** it asks whether the customer needs anything else.
6. **Given** the agent asked that, **When** the customer confirms they need nothing else, **Then** the agent closes politely and uses the tool that finishes the conversation.

*Store data and payment*

7. **Given** the question "Quais opções de violões disponíveis custando até R$1000?", **When** the agent answers, **Then** it lists options found by the product search, with their prices.
8. **Given** the question "Quanto custa o Takamine GD20?", **When** the agent answers, **Then** the price comes from the product lookup.
9. **Given** the question "Qual o endereço da loja?", **When** the agent answers, **Then** the answer comes from the policy lookup.
10. **Given** a price and a number of installments, **When** a customer asks if they can pay that way, **Then** the amounts and the answer come from the payment tool, including when the installment is below the minimum.
11. **Given** a product with an active promotion, **When** its price is shown, **Then** the agent shows the original price and the discount percentage, and does not apply the PIX discount on top of it.

*Special situations (sections 7.1 and 7.3)*

12. **Given** a product out of stock, **When** a customer asks for it, **Then** the agent says it is temporarily unavailable and suggests similar products that are in stock.
13. **Given** a discontinued product, **When** a customer asks for it, **Then** the agent says it is no longer in the catalog and offers equivalent models.
14. **Given** a promotion that is no longer active, **When** a customer asks about it, **Then** the agent says so openly and gives the current price.
15. **Given** a complaint, **When** a customer makes it, **Then** the agent listens with empathy, records it with the complaint tool, and says the store will reply within 24 business hours.
16. **Given** a request for an accessory (strings, cables, picks, pedals, amplifiers or cases), **When** a customer makes it, **Then** the agent politely explains that the store only sells musical instruments.
17. **Given** a message outside business hours, **When** the agent replies, **Then** it says when the store's team returns.

---

### User Story 2 - Check an order with identity verification (Priority: P2)

A customer asks about their order and provides the order number, phone and email. The agent shares the order's details only if all three match.

**Why this priority**: Order questions are a main reason customers contact the store, and showing an order to the wrong person is the most serious failure the agent could have.

**Independent Test**: Ask about an order with correct details, then again with a wrong phone, a wrong email, and each missing, and confirm details appear only in the first case.

**Acceptance Scenarios**:

1. **Given** an order, **When** a customer provides its number and the phone and email on that order, **Then** the agent shares the order's status and details.
2. **Given** an order, **When** the phone or the email is missing, **Then** the agent asks for it and shares nothing about the order.
3. **Given** an order, **When** the phone or the email does not match, **Then** the agent shares nothing, in a reply that does not reveal whether the order or the customer exists.
4. **Given** two customers with the same email, **When** one provides the other's order number with the shared email and their own phone, **Then** the agent shares nothing.
5. **Given** "Me arrependi da minha compra, posso devolver meu pedido?", **When** the customer is verified, **Then** the answer applies the return rules from the manual to that order.

---

### User Story 3 - Continue a conversation (Priority: P2)

A customer can ask follow-up questions without repeating themselves. A customer whose identity was verified can continue their open conversation after a page reload, once verified again. Anyone else's conversation lasts only for the session.

**Why this priority**: Follow-up questions are part of a normal text conversation, and returning customers should not have to start over.

**Independent Test**: Ask a follow-up in one session. Verify a customer, reload the page, verify again, and confirm the conversation continues. Repeat without verifying, and after using the new conversation button, and confirm it does not.

**Acceptance Scenarios**:

1. **Given** a conversation in progress, **When** the customer asks a follow-up question, **Then** the agent answers using the earlier messages.
2. **Given** a customer who was not verified, **When** the session ends, **Then** the agent no longer holds that conversation.
3. **Given** a verified customer with an open conversation, **When** they reload the page and are verified again, **Then** the agent finds that conversation and continues it.
4. **Given** a conversation in progress, **When** the customer uses the new conversation button, **Then** a modal asks them to confirm in Portuguese, and only on confirming does the conversation close, so the agent does not continue it. Cancelling keeps the conversation as it was.
5. **Given** a conversation with no message for 30 minutes, **When** the customer sends another message, **Then** the conversation has closed and the message starts a new one.

---

### User Story 4 - Keep working and diagnose failures (Priority: P3)

When the main model or a service fails, the agent uses the fallback, and a developer can find out what happened from the terminal, while the customer sees no technical details.

**Why this priority**: The self-hosted server can be unavailable during a demo, and today a failure with troubleshooting off leaves no trace.

**Independent Test**: Stop access to the primary model and confirm the agent answers through the fallback. Make every provider fail and confirm the customer sees the friendly message and the terminal shows the cause.

**Acceptance Scenarios**:

1. **Given** the primary model is unavailable, **When** a customer sends a message, **Then** the fallback answers and the troubleshooting view records that it was used.
2. **Given** any failure, **When** troubleshooting is off, **Then** the terminal records the cause with secrets removed, and the page shows only the friendly message.
3. **Given** the selected agent cannot start, **When** the application starts, **Then** the terminal records the cause with secrets removed, and the page stays as specified in the chat feature.

---

### Edge Cases

- A store rule the manual contradicts itself on is answered as recorded in `docs/stakeholder-clarifications.md`.
- An order whose stored total differs from its items is quoted at the stored total, as recorded in `docs/corner-cases/store-data.md`.
- A search that finds nothing leads the agent to say so and point to the store's contact channels, instead of guessing.
- A customer verified on one order asks about another order, which needs its own verification.
- **Page reload**: the page starts empty in a new session. An identified customer's conversation stays open, so they can continue it by verifying again. Any other conversation is lost.

## Requirements *(mandatory)*

### Functional Requirements

#### Agent

- **FR-001**: The agent MUST replace the stand-in as the default agent, behind the existing agent interface.
- **FR-002**: The agent MUST work as one agent that decides which of the tools in the Agent Tools table to use, and can use several for one question.
- **FR-003**: Prices, stock, promotions and order details MUST come from a lookup made for that answer, and store rules from the policy manual.
- **FR-004**: Calculated values, such as installments and discounts, MUST come from a tool, following the rules in the manual and `docs/stakeholder-clarifications.md`.
- **FR-005**: The agent MUST reply in Brazilian Portuguese, in the tone set by section 7.1 of the manual, and follow the service flow in section 7.2 and the special situations in sections 7.1 and 7.3.
- **FR-006**: The agent MUST try the self-hosted model first and use the hosted provider as its fallback.
- **FR-007**: Each reply MUST record its tools, sources, model, provider and fallback use in the reply details.

#### Orders

- **FR-008**: Order details MUST be shared only when the order number, phone and email all match that order's customer, checked outside the model's control.
- **FR-009**: A failed check MUST NOT reveal whether the order or the customer exists.

#### Conversations

- **FR-010**: A customer MUST count as identified once they pass the order check in FR-008.
- **FR-011**: Identified customers' conversations MUST be stored in a dedicated table in the store's database, held by a system user ID, with their personal information obfuscated. This is the one exception to FR-018 of the chat feature.
- **FR-012**: When a customer is verified, the agent MUST use a tool to find that customer's open conversation and continue it, if there is one.
- **FR-013**: Conversations of customers who were not identified MUST NOT be stored, and MUST last only for the session.
- **FR-014**: The new conversation button MUST ask for confirmation in a modal. A conversation MUST close when the customer confirms in that modal, which tells the agent to forget it, when the agent uses the tool that finishes the conversation, or after 30 minutes without a message. A closed conversation MUST NOT be continued. A page reload starts a new session and does not close a conversation.
- **FR-015**: Conversations of different customers and sessions MUST never mix.

#### Failures and improvements

- **FR-016**: Failures MUST be logged to the terminal with secrets removed, and nothing new from them may reach the page, as recorded in `docs/pending-updates.md`.
- **FR-017**: An agent call that ends with no result MUST be reported as a failure, not a timeout.
- **FR-018**: Values under sensitive names MUST be removed whatever their type, including lists and numbers.
- **FR-019**: Reply details with a text in place of the list of errors MUST count as invalid.
- **FR-020**: Clearing the text in the long-message panel and sending it MUST close the panel, instead of leaving the old error on screen.
- **FR-021**: The effect of Streamlit's Stop button during a wait MUST be verified, and fixed if it leaves the page unusable.

#### Agent Tools

- **FR-022**: The agent MUST have exactly the tools below. Each description MUST tell the model when to use the tool.
- **FR-023**: Sections 7, 7.1, 7.2, 7.3 and 10 of the manual are staff guidance for the agent's instructions, and MUST NOT be returned by the policy lookup.
- **FR-024**: Customer identity MUST come from the order check, never from a value the model provides.

| Tool | Use it when | Takes | Returns |
|---|---|---|---|
| `search_products` | The customer looks for options, or a similar in-stock product is needed | Text, category, maximum price, whether it must be in stock | Matching products with price, stock, status and any active promotion |
| `get_product` | The customer asks about a specific product | Product name | Price, stock, status, specs, and for an active promotion the original price, discount percentage and final price |
| `payment_terms` | The customer asks how to pay, or about installments or discounts | Product or amount, payment method, number of installments | Final price, installment value, the minimum that applies, and whether it is allowed |
| `policy_lookup` | The customer asks about a store rule or the store itself | The question | The matching sections of the manual, with their numbers |
| `get_order_status` | The customer asks about an order | Order number, phone, email | If all match: status, total, payment, items, tracking code, delivery estimate, and days since that estimate. Otherwise the same reply for every failure |
| `find_open_conversation` | Right after a customer passes the order check | Nothing, it uses the verified customer | The customer's open conversation, if there is one |
| `register_complaint` | The customer makes a complaint | A summary of the complaint | Confirmation that it was recorded, and the 24 business hours return time |
| `finish_conversation` | The customer has confirmed they need nothing else | Nothing | Confirmation that the conversation closed |

### Key Entities

- **Customer**: a person in the store data, identified by the system user ID once verified.
- **Stored conversation**: an identified customer's messages, held by system user ID with personal information obfuscated, either open or closed.
- **Session**: one page's time in the chat, which ends on a page reload, the new conversation button or 30 minutes without a message.
- **Tool**: a defined action the agent can take, listed in the Agent Tools table.
- **Complaint**: what a customer complained about and when, stored for the store's team, with personal information obfuscated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the real model, the four sample questions in the brief, one installment question, one order question with identity check and each special situation in User Story 1 get the expected behavior.
- **SC-002**: In a test of order questions with a wrong or missing phone or email, including customers who share an email, 0 replies share order details.
- **SC-003**: After a page reload, a verified customer continues their open conversation once verified again. A customer who was not verified, or whose conversation closed, continues nothing.
- **SC-004**: Inspecting the stored conversations finds 0 names, phones or emails in readable form.
- **SC-005**: With the primary model unavailable, the sample questions are still answered through the fallback.
- **SC-006**: With troubleshooting off, 100% of failures appear in the terminal, with 0 secrets, and 0 technical details appear on the page.

## Assumptions

- **Existing interface**: the chat, its troubleshooting view and its 60-second reply limit stay as specified in `specs/001-streamlit-chat/`, apart from what this feature changes.
- **Existing data**: the store data and the committed policy index are the sources, and the agent only reads them. It writes only stored conversations and complaints.
- **Current date and time**: the agent knows them, for business hours and return periods.
- **Delivery dates**: the store data has a delivery estimate but no actual delivery date, so return periods count from the estimate.
- **Partner stores**: the manual suggests recommending them when possible, but names none, so the agent names none.
- **Stored conversations**: a closed conversation stays stored, and is not continued.
- **Contact and rule conflicts**: handled as recorded in `docs/stakeholder-clarifications.md`.
