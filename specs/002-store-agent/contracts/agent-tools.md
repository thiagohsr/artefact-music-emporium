# Contract: Agent Tools

The spec's Agent Tools table says what each tool is for. This adds the types and rules. Each tool returns a typed
result, and expected outcomes are data, not exceptions.

| Tool | Parameters | Result |
|---|---|---|
| `search_products` | `text`, `category`, `min_price_brl`, `max_price_brl`, `in_stock_only`, all optional | Up to 10 products: name, category, price, stock, status, promotion |
| `get_product` | `name` | One product with specs and promotion, a list of close matches, or not found |
| `payment_terms` | `installments` (required), `product_name` or `amount_brl`, and `method` (`credit` by default) | See below |
| `policy_lookup` | `question` | Up to 3 customer sections: number, title, text |
| `get_order_status` | `order_number`, `phone`, `email` | The order, or one fixed "not verified" result |
| `find_open_conversation` | None | The masked transcript, or none |
| `register_complaint` | `summary` | Recorded, and the 24 business hours return time |
| `finish_conversation` | None | Closed |

## Products

- A promotion is included only when `is_active` is true, as original price, discount percentage and final price.
- The price range includes both limits, and compares against the price the customer would pay, which is the final price
  when a promotion is active. Either limit can be given alone.
- `search_products` leaves out discontinued products unless the customer named one, which `get_product` handles.
- Status is always returned, so the agent can apply sections 7.1 and 7.3. A `coming_soon` product is reported as not yet
  available, whatever its stock says.

## payment_terms

No database access beyond the product's price. All money uses `Decimal`.

| Method | Rule |
|---|---|
| `pix` | 5% off the list price. No discount on a promotional price |
| `debit`, `boleto` | List or promotional price, paid at once |
| `credit` | Up to 12x with no interest. Minimum installment: R$ 50 up to 3x, R$ 80 from 4x to 6x, R$ 100 from 7x to 12x |

Returns the final price, the installment value, the minimum that applies, `allowed`, and when not allowed, a `reason`:
`below_minimum` or `too_many_installments`.

## get_order_status

- All three values are required by the tool's signature, so the model must ask for what's missing.
- The order is looked up first, then the phone (digits only) and email (ignoring case) are compared with that order's
  customer. Any failure gives the same result, including an order that doesn't exist.
- On success it returns status, order date, stored total, payment method, items, tracking code, delivery estimate and
  days since that estimate, and it records the customer in the session.
- The stored total is returned as it is, never recalculated.

## Agent interface

```python
class Agent(Protocol):
    name: str
    is_simulated: bool

    def respond(self, conversation_id: str, message: str) -> AgentReply: ...
    def end_conversation(self, conversation_id: str) -> None: ...
```

The stand-in gets a method that does nothing. `end_conversation` must not raise for an unknown ID.
