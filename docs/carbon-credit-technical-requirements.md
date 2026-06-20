# Technical Requirements Document: Farmer Carbon Credit Marketplace (v1)

## 1. Purpose
Translate the [Farmer Carbon Credit Marketplace PRD](./carbon-credit-prd.md) into an implementation-ready technical blueprint for an MVP release.

## 2. Scope Alignment (from PRD)

### In scope (v1)
- Supplier onboarding and project intake
- Operations eligibility/review workflow
- Offer management and acceptance lifecycle
- Contract and payout status tracking
- Inventory creation and listing management
- Buyer catalog, quote/purchase, transfer, and retirement
- Audit log and basic reporting

### Out of scope (v1)
- Carbon registry creation
- In-house scientific verification engine
- Blockchain/tokenization settlement
- Open secondary trading

## 3. Target System Architecture

### 3.1 Components
1. **Web App (Buyer + Operations + Supplier portals)**
   - Role-based views for supplier, buyer, and internal operator.
2. **Backend API**
   - REST API for all workflows.
   - Authentication, authorization, business rules, and orchestration.
3. **Relational Database**
   - Source of truth for users, projects, offers, contracts, inventory, orders, and retirements.
4. **Document Storage**
   - Stores supplier uploads and verification artifacts (MRV docs, contracts, proofs).
5. **Async Worker/Queue**
   - Handles long-running tasks (document processing, notifications, report generation).
6. **Notification Service**
   - Email notifications for status transitions (submission received, offer created, purchase complete).

### 3.2 High-level flow
Supplier submits project -> Operator reviews and scores -> Offer and contract finalized -> Inventory created/listed -> Buyer purchases -> Transfer/retirement recorded -> Reports generated.

## 4. Roles and Access Control
- **Supplier**: manage own profile/projects/documents, review offers, track payouts.
- **Buyer**: browse listings, request quote or purchase, view retirements.
- **Operator**: review projects, manage offers/contracts, inventory, and risk checks.
- **Admin**: manage users, policies, and system-level configurations.

Access control must be role-based, deny-by-default, and enforce tenant/data ownership boundaries.

## 5. Functional Technical Requirements

### 5.1 Supplier Onboarding & Intake
- Supplier account registration with email verification.
- Profile fields: geography, land size, crop/livestock type, ownership/lease status, payout details.
- Project submission form with draft + submitted states.
- Document upload support for registry evidence, MRV records, land ownership proofs.
- Validation rules for required fields before submission.

### 5.2 Eligibility & Operations Review
- Review queue with statuses: `new`, `in_review`, `needs_info`, `approved`, `rejected`.
- Scoring form for quality, readiness, and risk dimensions.
- Decision reason logging (required on reject/needs-info).
- Full status timeline with actor + timestamp.

### 5.3 Offer & Contract Management
- Operator can create versioned offers per project.
- Offer includes pricing model, fees, payout schedule, delivery expectations, liability clauses.
- Supplier can accept/reject/counter (counter optional for v1).
- Contract record generated upon acceptance; immutable signed snapshot stored.

### 5.4 Inventory & Listing
- Inventory unit model supports issued and forward supply.
- Inventory states: `reserved`, `available`, `sold`, `retired`.
- Listing management: create, publish, unpublish, set price/volume constraints.
- Prevent overselling with transactional inventory locking.

### 5.5 Buyer Commerce
- Search + filter by geography, methodology, registry, vintage, co-benefits, price.
- Listing detail page with quality metadata and supporting evidence.
- Checkout flow for direct purchase and quote-request flow.
- Order lifecycle statuses: `initiated`, `pending_payment`, `paid`, `transferred`, `retired`.

### 5.6 Transfer, Retirement, Reporting
- Retirement event record with quantity, date, beneficiary, and certificate reference.
- Downloadable retirement confirmation for buyers.
- Supplier and buyer transaction history endpoints.
- Operator audit reports for inventory ownership and status changes.

## 6. Data Model (Minimum Entities)
- `users` (id, role, org_id, status)
- `supplier_profiles` (user_id, farm metadata, payout metadata)
- `projects` (supplier_id, methodology, geography, status)
- `project_documents` (project_id, type, storage_uri, checksum)
- `reviews` (project_id, reviewer_id, score_json, decision, reason)
- `offers` (project_id, version, terms_json, status)
- `contracts` (offer_id, signed_at, document_uri, terms_snapshot)
- `inventory_lots` (project_id, issuance_type, quantity_total, quantity_available, status)
- `listings` (inventory_lot_id, published, price, currency, metadata_json)
- `orders` (buyer_id, listing_id, quantity, total_price, status)
- `payments` (order_id, provider_ref, status, paid_at)
- `retirements` (order_id, quantity, retired_at, certificate_uri)
- `audit_logs` (actor_id, entity_type, entity_id, action, before_json, after_json, created_at)

## 7. API Requirements (MVP)
- REST + JSON, versioned as `/api/v1`.
- OpenAPI spec required before implementation freeze.
- Required endpoint groups:
  - Auth and user profile
  - Supplier projects and documents
  - Review queue and decisions
  - Offers and contracts
  - Inventory and listings
  - Buyer catalog, order, payment
  - Transfer/retirement and reports
- Idempotency keys required for payment and order-creation endpoints.
- Pagination and filtering required for list endpoints.

## 8. Non-Functional Requirements
- **Security**
  - Authentication required for all non-public endpoints.
  - RBAC enforcement on every protected endpoint.
  - Encryption in transit (TLS) and at rest for sensitive files/data.
  - Immutable audit trail for critical actions.
- **Performance**
  - Catalog search API p95 <= 800ms for a dataset of up to 50,000 active listings.
  - Standard read endpoints p95 <= 500ms at up to 100 requests/second and 500 concurrent users.
- **Reliability**
  - Target API availability >= 99.5% monthly for MVP.
  - Retries + dead-letter handling for async jobs.
- **Observability**
  - Structured logs with correlation IDs.
  - Metrics dashboards for submission volume, approval rates, conversion, retirement throughput.
- **Compliance**
  - Data retention and access logs for contract and retirement records.

## 9. Delivery Plan (Technical Milestones)

### Milestone 1: Foundations
- Auth + RBAC
- Core database schema
- Supplier onboarding and project intake
- Document upload service

### Milestone 2: Operations
- Review workflow and scoring
- Offer versioning and contract storage
- Audit logging foundation

### Milestone 3: Marketplace
- Inventory and listing management
- Buyer search/detail/checkout
- Payment + order lifecycle

### Milestone 4: Settlement & Reporting
- Transfer and retirement workflow
- Downloadable confirmation artifacts
- Supplier/buyer/operator reporting

## 10. Acceptance Criteria for MVP Release
- End-to-end scenario works: supplier submission -> approval -> offer acceptance -> listing -> buyer purchase -> retirement -> report.
- No unauthorized cross-role/cross-tenant data access in validation testing.
- Inventory cannot be oversold in concurrent purchase attempts.
- All critical actions produce auditable event records.
- Public and protected APIs conform to published OpenAPI contract.
