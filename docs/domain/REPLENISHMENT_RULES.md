# Replenishment Rules

- `Replenishment` is the aggregate root; terminal states (`COMPLETED` / `CANCELLED`) are immutable.
- Line quantity is signed: `> 0` load, `< 0` unload, `0` invalid.
- Capacity rule per operation: `0 < abs(quantity) <= capacity` (not cumulative stock).
- `unit_price` is historical on the line; do not reconstruct from current slot price.
- Substitution when `product_id != preferred_product_id` requires reason and matching configured price.
- Preferred product on the slot is **not** mutated by replenishment.
- Snapshots: `product_description_snapshot`, `preferred_product_id_snapshot`, `replacement_reason`.
