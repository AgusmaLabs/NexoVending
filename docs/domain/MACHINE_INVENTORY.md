# Machine Inventory

```text
theoretical = opening + replenishment_net - consumption
variance = physical - theoretical
next.opening = previous.physical
```

- First period `opening_quantity = 0`.
- No artificial `OPENING_BALANCE` movement.
- Variance is observed, not an automatic `LOSS`.
- Capacity changes on the slot do not invent inventory loss.
