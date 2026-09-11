* [x] V0 Bootstrap

* [x] V1 Foundation & Domain Contracts

* [x] V3 Identity & Operator Management

* [x] V4 Product Catalog

* [x] V5 Machine & Slot Management

* [x] V6 Inventory Ledger

* [x] V7 Platform Integration Review

     └─ arquitectura, DB, Session, UoW, tenant, repositorios

     └─ UoW genérico exigido en NexoPlatform (entregado en 1.3–1.10)

* [x] V8 Persistence

        └─ nexo-platform==1.10.0 (TransactionalUnitOfWork + Database)

        └─ PostgreSQL + SQLAlchemy + repositories + UoW

        └─ atomicidad

        └─ multi-tenancy

* [x] V9 API (Replenishment & Inventory)

        └─ FastAPI inbound adapter

        └─ RequestContext / authz / entitlement

        └─ Platform Idempotency + Observability

        └─ OpenAPI + API tests (PostgreSQL)

* [ ] V10 Reliability / concurrency hardening (beyond V8/V9 coverage)

* [ ] V11 Flutter Mobile

        └─ online-first

* [ ] V12 Offline & Sync

* [ ] V13 Admin Web

* [ ] V14 Alerts & Audit

* [ ] V15 Production Hardening
