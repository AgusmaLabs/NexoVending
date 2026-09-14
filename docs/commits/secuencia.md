* [x] V0 Bootstrap
* [x] V1 Foundation & Domain Contracts
* [x] V3 Identity & Operator Management
* [x] V4 Product Catalog
* [x] V5 Machine & Slot Management
* [x] V6 Inventory Ledger
* [x] V7 Platform Integration Review
* [x] V8 Persistence
* [x] V9 API (Replenishment & Inventory)
* [x] V10 Replenishment Execution Context
        └─ ResolveMachine / MachineAssignment / slots / barcode
        └─ inventory check on add-line
        └─ GPS capture without geofencing
* [x] V11 Unresolved Product on Replenishment
        └─ PENDING_PRODUCT_RESOLUTION lines (manual_description, product_id null)
        └─ Complete writes movements only for RESOLVED lines
        └─ Admin ResolveReplenishmentLineProduct + deferred inventory
* [x] V12 Mobile Session JWT Facade
        └─ bump nexo-platform==1.11.0
        └─ POST /api/v1/auth/session (issue_session) + decode_session on business routes
        └─ GET /api/v1/operators/me; harness principal/... preserved
* [ ] V13 Flutter Mobile
* [ ] V14 Offline & Sync
* [ ] V15 Admin Web
* [ ] V16 Alerts & Audit
* [ ] V17 Production Hardening
