# Procurement App — Claude Context Pointer

You're working in the procurement app, which holds:
- Core data models: `Supplier`, `Category`, `Transaction`, `DataUpload`
- P2P models: `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `Invoice`

If your task touches any P2P model or workflow, read **[../../../docs/claude/p2p.md](../../../docs/claude/p2p.md)** first — it documents architectural invariants, the canonical primitives, and known divergences you must not "fix".

For accuracy conventions affecting all analytics, see root CLAUDE.md § "Analytics accuracy conventions" and `docs/ACCURACY_AUDIT.md`.
