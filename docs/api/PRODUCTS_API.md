# Products HTTP API (replenishment capture)

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/products/barcode/{barcode}` | `product.read` |

- Found → 200 product DTO  
- Missing → 404 (`product not found`)  
- Never auto-creates catalog products  
- Tenant from `RequestContext` only
