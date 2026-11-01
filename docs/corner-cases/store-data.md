# Store Data Corner Cases

Issues found in the source CSVs (`data/csv_origin/`) while building the SQLite database. The data is
loaded unchanged. The handling below is proposed for the agent and is not implemented yet.

| # | Case | Records | Affects | Status |
|---|---|---|---|---|
| 1 | Shared customer email | Customers 11 and 43 | Identity check for order details | Needs confirmation |
| 2 | Order total differs from its items | Orders 3 and 20 | Order totals quoted to customers | Needs confirmation |

## 1. Shared customer email

**Finding**: customers 11 and 43 have the same email address, so `customers.email` cannot be unique.
The other 48 customers each have their own address.

**Risk**: looking up a customer by email could return the wrong person. If verification relies on
that lookup, one customer could see the other's orders, which Principle III of the constitution
prohibits.

**Proposed handling**: start from the order and match the email or phone given by the person against
the customer linked to that order. Do not identify a customer by email alone. Test this with both
customers, using an order that belongs to only one of them.

**Question for the store**: are these two customers different people sharing an address, or is one
of the records wrong?

## 2. Order total differs from its items

**Finding**: two orders have totals below the sum of current product price times quantity.

| Order | Payment | Stored total | Sum of items | Difference |
|---|---|---|---|---|
| 3 | `credit_12x` | R$ 3,450.00 | R$ 3,498.00 | R$ 48.00 |
| 20 | `credit_3x` | R$ 1,400.00 | R$ 1,488.00 | R$ 88.00 |

**Cause**: unknown. The PIX discount does not explain it, since both orders were paid by credit card.
A promotion at purchase time or a later price change is possible, but the data does not show either.

**Proposed handling**: quote the stored `total_brl` and do not recalculate it from current prices. Do
not present a cause to the customer unless the store confirms one.

**Question for the store**: do order totals keep the prices and discounts from the purchase date, or
are these two totals wrong?
