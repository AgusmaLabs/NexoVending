# Inventory Custody & Reconciliation

## Administrator / Replenisher

```text
expected (ledger) → physical count → variance → (optional explicit LOSS/ADJUSTMENT)
```

Expected inventory is available continuously from movements. Physical verification is separate.

## Machine

```text
opening → replenishments → consumption → theoretical → physical → variance → next opening
```

## Explicit loss only

Variance never auto-creates `LOSS`. An operator must register an explicit loss/adjustment after investigation.
