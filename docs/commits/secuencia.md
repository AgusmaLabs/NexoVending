* [x] V0 Bootstrap 



* [x] V1 Foundation & Domain Contracts



* [x] V3 Identity & Operator Management



* [x] V4 Product Catalog



* [x] V5 Machine & Slot Management



* [x] V6 Inventory Ledger



* [x] V7 Platform Integration Review



     └─ arquitectura, DB, Session, UoW, tenant, repositorios



     └─ UoW genérico exigido en NexoPlatform (entregado en 1.3–1.7)



* [x] V8 Persistence

        └─ nexo-platform==1.7.0 (TransactionalUnitOfWork + Database)

        └─ PostgreSQL + SQLAlchemy + repositories + UoW

        └─ atomicidad

        └─ multi-tenancy



* [ ] V9 Concurrency & Robustness



        └─ locking



        └─ race conditions



        └─ invariants



        └─ PostgreSQL integration tests



* [ ] V10 Application



        └─ Replenishment Application



        └─ Inventory Application



        └─ Sales/Consumption Application



        └─ orchestration



* [ ] V11 Vending API



        └─ REST endpoints



        └─ DTOs



        └─ authentication/context



* [ ] V12 Reliability



        └─ idempotency



        └─ retries



        └─ conflict handling



        └─ operation deduplication



* [ ] V13 Flutter Mobile



        └─ online-first



* [ ] V14 Offline & Sync



        └─ local queue



        └─ retry



        └─ synchronization



        └─ conflict resolution



* [ ] V15 Admin Web



* [ ] V16 Alerts & Audit



* [ ] V17 Production Hardening

