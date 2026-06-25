# Farmer Carbon Credit Marketplace - System Architecture

## Overview
This document provides a detailed system architecture for the Farmer Carbon Credit Marketplace MVP, derived from the technical requirements.

---

## 1. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Supplier Portal │  │   Buyer Portal   │  │  Ops Portal      │  │
│  │   (Web App)      │  │   (Web App)      │  │   (Web App)      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │            │
└───────────┼─────────────────────┼──────────────────────┼────────────┘
            │                     │                      │
            └─────────────────────┼──────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  API Gateway / Load Bal.   │
                    └─────────────┬──────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   REST API       │    │  Auth Service    │    │  Notification    │
│   Endpoints      │    │  (OAuth2/JWT)    │    │  Service         │
│                  │    │                  │    │                  │
│ • User/Auth      │    │ • Token mgmt     │    │ • Email queue    │
│ • Projects       │    │ • RBAC checks    │    │ • Event trigger  │
│ • Reviews        │    │ • MFA support    │    │ • Delivery       │
│ • Offers         │    │                  │    │                  │
│ • Inventory      │    └──────────────────┘    └──────────────────┘
│ • Orders         │
│ • Retirements    │
│ • Audit logs     │
└────────┬─────────┘
         │
    ┌────┴──────────────────────��──────────────────┬──────────────┐
    │                           │                  │              │
    ▼                           ▼                  ▼              ▼
┌──────────────────────┐  ┌──────────────────┐  ┌────────────┐  ┌────────────┐
│  Business Logic      │  │  Document Mgmt   │  │  Payment   │  │  Async     │
│  Layer               │  │  Service         │  │  Service   │  │  Worker    │
│                      │  │                  │  │            │  │  Queue     │
│ • Eligibility rules  │  │ • Upload handler │  │ • Provider │  │            │
│ • Offer generation   │  │ • Validation     │  │   integration│ │ • Processing│
│ • Inventory logic    │  │ • Versioning     │  │ • Status   │  │ • Reporting│
│ • Order workflows    │  │ • Checksum verify│  │   tracking │  │ • Notifications│
│ • Retirement flows   │  │                  │  │ • Idempotency│  │ • Auditing │
└──────────┬───────────┘  └────────┬─────────┘  └─────┬──────┘  └──────┬─────┘
           │                       │                  │               │
    ┌──────┴───────────────────────┼──────────────────┼───────────────┘
    │                              │                  │
    ▼                              ▼                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                      DATA PERSISTENCE LAYER                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────┐         ┌──────────────────────────┐   │
│  │  Relational Database │         │  Document Storage        │   │
│  │  (PostgreSQL)        │         │  (S3 / Cloud Storage)    │   │
│  │                      │         │                          │   │
│  │ Tables:              │         │ • MRV documents          │   │
│  │ • users              │         │ • Registry evidence      │   │
│  │ • supplier_profiles  │         │ • Contracts (PDF)        │   │
│  │ • projects           │         │ • Ownership proofs       │   │
│  │ • reviews            │         │ • Retirement certs       │   │
│  │ • offers             │         │ • Verification artifacts │   │
│  │ • contracts          │         │                          │   │
│  │ • inventory_lots     │         │ Storage Format:          │   │
│  │ • listings           │         │ • URI: s3://bucket/path  │   │
│  │ • orders             │         │ • Checksum validation    │   │
│  │ • payments           │         │ • Versioning support     │   │
│  │ • retirements        │         │ • Access control via DB  │   │
│  │ • audit_logs         │         │                          │   │
│  │ • project_documents  │         └──────────────────────────┘   │
│  │                      │                                        │
│  │ Backup & HA:         │         ┌──────────────────────────┐   │
│  │ • Replication        │         │  Cache Layer             │   │
│  │ • Point-in-time      │         │  (Redis)                 │   │
│  │   recovery           │         │                          │   │
│  │                      │         │ • Session tokens         │   │
│  └──────────────────────┘         │ • Frequently accessed    │   │
│                                   │   data (listings)        │   │
│                                   │ • Rate limiting counters │   │
│                                   │                          │   │
│                                   └──────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Component Architecture

### 2.1 Client Layer

#### Supplier Portal
- **Features**: Profile management, project submission, document uploads, offer review, payout tracking
- **Technologies**: React/Vue.js, TypeScript, form validation
- **Key Pages**:
  - Onboarding & profile setup
  - Project creation wizard
  - Document upload dashboard
  - Offer management
  - Transaction history

#### Buyer Portal
- **Features**: Browse listings, search & filter, quote requests, purchase orders, retirement tracking
- **Technologies**: React/Vue.js, TypeScript, search UI
- **Key Pages**:
  - Catalog with filters (geography, methodology, vintage, etc.)
  - Listing detail with evidence
  - Checkout & order confirmation
  - Retirement certificates
  - Purchase history

#### Operations Portal
- **Features**: Review projects, score submissions, create offers, manage contracts, inventory, audit logs
- **Technologies**: React/Vue.js, TypeScript, dashboards
- **Key Pages**:
  - Review queue dashboard
  - Scoring form
  - Offer & contract builder
  - Inventory management
  - Analytics & reporting

---

### 2.2 API Gateway & Load Balancing

**Purpose**: Single entry point for all client requests, authentication routing, rate limiting

**Responsibilities**:
- Route requests to appropriate backend services
- SSL/TLS termination
- Rate limiting (API key / user-based)
- CORS handling
- Request/response logging
- DDoS protection

**Technologies**: NGINX, AWS API Gateway, or Kong

---

### 2.3 REST API Endpoints (v1)

#### Authentication
```
POST   /api/v1/auth/register         - Supplier/buyer registration
POST   /api/v1/auth/login            - User login
POST   /api/v1/auth/refresh          - Token refresh
POST   /api/v1/auth/logout           - User logout
POST   /api/v1/auth/verify-email     - Email verification
```

#### User & Profile
```
GET    /api/v1/users/me              - Get current user profile
PUT    /api/v1/users/me              - Update profile
GET    /api/v1/users/{id}            - Get user details (admin)
```

#### Supplier Projects
```
GET    /api/v1/suppliers/projects           - List supplier's projects
POST   /api/v1/suppliers/projects           - Create new project (draft)
GET    /api/v1/suppliers/projects/{id}      - Get project details
PUT    /api/v1/suppliers/projects/{id}      - Update project
POST   /api/v1/suppliers/projects/{id}/submit - Submit for review
```

#### Project Documents
```
POST   /api/v1/projects/{id}/documents       - Upload document
GET    /api/v1/projects/{id}/documents       - List documents
DELETE /api/v1/projects/{id}/documents/{doc_id} - Remove document
```

#### Review & Scoring
```
GET    /api/v1/reviews/queue                - Get projects in review
GET    /api/v1/reviews/{project_id}         - Get review status
POST   /api/v1/reviews/{project_id}/score   - Submit scoring form
POST   /api/v1/reviews/{project_id}/decide  - Approve/reject/needs-info
GET    /api/v1/reviews/{project_id}/timeline - Get status timeline
```

#### Offers & Contracts
```
GET    /api/v1/projects/{id}/offers         - List offers for project
POST   /api/v1/projects/{id}/offers         - Create offer (operator)
GET    /api/v1/offers/{id}                  - Get offer details
POST   /api/v1/offers/{id}/accept           - Supplier accepts offer
POST   /api/v1/offers/{id}/reject           - Supplier rejects offer
GET    /api/v1/contracts/{id}               - Get signed contract
```

#### Inventory & Listings
```
GET    /api/v1/inventory                    - List inventory lots
POST   /api/v1/inventory                    - Create inventory lot
GET    /api/v1/inventory/{id}               - Get lot details
PUT    /api/v1/inventory/{id}               - Update lot
GET    /api/v1/listings                     - Browse published listings
GET    /api/v1/listings/{id}                - Get listing detail
POST   /api/v1/listings                     - Create listing
PUT    /api/v1/listings/{id}                - Update listing (price, visibility)
POST   /api/v1/listings/{id}/publish        - Publish listing
POST   /api/v1/listings/{id}/unpublish      - Unpublish listing
```

#### Buyer Commerce
```
GET    /api/v1/catalog/search               - Search listings (with filters)
GET    /api/v1/catalog/listings/{id}        - Get listing with evidence
POST   /api/v1/orders                       - Create order (idempotent)
GET    /api/v1/orders/{id}                  - Get order status
GET    /api/v1/orders                       - List buyer's orders
```

#### Payments
```
POST   /api/v1/payments                     - Initiate payment (idempotent)
GET    /api/v1/payments/{id}                - Get payment status
POST   /api/v1/payments/{id}/confirm        - Confirm payment webhook
```

#### Transfer & Retirement
```
POST   /api/v1/orders/{id}/transfer         - Record transfer
POST   /api/v1/orders/{id}/retire           - Record retirement
GET    /api/v1/retirements/{id}             - Get retirement details
GET    /api/v1/retirements/{id}/certificate - Download certificate (PDF)
```

#### Reporting
```
GET    /api/v1/suppliers/reports/transactions - Supplier transaction history
GET    /api/v1/buyers/reports/retirements     - Buyer retirement history
GET    /api/v1/operator/reports/audit         - Operator audit logs
GET    /api/v1/operator/reports/analytics     - System analytics dashboard
```

---

### 2.4 Authentication Service

**Technologies**: OAuth2 + JWT, MFA (optional for v1)

**Responsibilities**:
- User registration & email verification
- Login & session management
- JWT token generation & validation
- Role-Based Access Control (RBAC) checks
- Password reset & account recovery

**Key Flows**:
```
Registration → Email Verification → Profile Setup → API Access
Login → 2FA (optional) → JWT Token → Request with Authorization header
Token Refresh → New JWT + Refresh Token
```

**Token Structure**:
```json
{
  "sub": "user_id",
  "role": "supplier|buyer|operator|admin",
  "org_id": "tenant_id",
  "email": "user@example.com",
  "permissions": ["project.create", "project.read", ...],
  "iat": 1234567890,
  "exp": 1234571490
}
```

---

### 2.5 Business Logic Layer

#### Eligibility & Validation Engine
- **Input**: Project submission data + documents
- **Rules**:
  - Required field validation
  - Geography & methodology compatibility
  - Land size constraints
  - Document type & format validation
  - MRV record completeness checks

#### Offer Generation Engine
- **Input**: Approved project + operator inputs
- **Logic**:
  - Calculate pricing based on project characteristics
  - Define payout schedule (milestone-based or lump sum)
  - Attach fee structure & liability clauses
  - Version management for offer iterations

#### Inventory Management Engine
- **Input**: Accepted offer + project terms
- **Logic**:
  - Create inventory lot with total quantity
  - Track issued vs. forward supply
  - Enforce state transitions (reserved → available → sold → retired)
  - Prevent overselling with transactional locking

#### Order Fulfillment Engine
- **Input**: Order creation request
- **Logic**:
  - Validate buyer & inventory availability
  - Lock inventory (transactional)
  - Create order record with unique ID
  - Trigger payment initiation
  - Handle cancellation/refund scenarios

#### Retirement Processing Engine
- **Input**: Paid order + retirement request
- **Logic**:
  - Validate order status (paid)
  - Decrement inventory available count
  - Create retirement record with timestamp
  - Generate certificate
  - Update buyer & supplier records
  - Trigger notifications

---

### 2.6 Document Management Service

**Responsibilities**:
- Secure file upload/download
- Virus scanning
- Format validation (PDF, DOCX, images)
- Checksum verification
- Document versioning
- Access control (only authorized users can access)

**Storage Architecture**:
```
S3 Bucket Structure:
/documents
  /{project_id}
    /{type}
      /{filename}
      /{filename}.metadata.json

Metadata JSON:
{
  "file_id": "uuid",
  "original_name": "...",
  "size": 1024,
  "mime_type": "application/pdf",
  "checksum": "sha256:...",
  "uploaded_by": "user_id",
  "uploaded_at": "2025-06-25T10:30:00Z",
  "access_control": ["supplier_123", "operator_456"],
  "retention_until": "2030-06-25"
}
```

**Security Controls**:
- Pre-signed URLs for temporary access
- Encryption at rest (AWS KMS)
- Virus scanning before storage
- Audit logging for all access

---

### 2.7 Payment Service

**Responsibilities**:
- Payment provider integration (Stripe, PayPal, etc.)
- Order-to-payment mapping
- Payment status tracking
- Webhook handling for provider callbacks
- Idempotency for concurrent payment requests

**Payment Flow**:
```
1. Order Created → Payment Service
2. Generate Payment Intent (idempotent key)
3. Return checkout URL to client
4. Client completes payment at provider
5. Provider sends webhook → Payment Service
6. Validate signature & idempotency
7. Update order status → paid
8. Trigger transfer/retirement workflow
9. Send confirmation email
```

**Idempotency Key Strategy**:
```
Key = HMAC-SHA256(order_id + buyer_id + timestamp, secret)
Store in Redis with TTL = 24 hours
Check before processing each payment request
```

---

### 2.8 Notification Service

**Responsibilities**:
- Event-driven notifications
- Template-based email generation
- Retry logic for failed sends
- Notification preferences management

**Event Types**:
```
Supplier Events:
- project_submitted
- project_approved
- project_rejected
- offer_created
- offer_accepted
- offer_rejected
- payout_scheduled
- payout_completed

Buyer Events:
- listing_available
- order_confirmed
- order_paid
- transfer_completed
- retirement_confirmed
- certificate_ready

Operator Events:
- new_project_submitted
- document_upload_complete
- review_reminder
- offer_created
```

**Architecture**:
```
Event → Message Queue (RabbitMQ/SQS)
      → Notification Worker (consumes events)
      → Template Engine (Handlebars/EJS)
      → Email Provider (SendGrid/SES)
      → Delivery Tracking
      → Retry Queue (with exponential backoff)
      → Dead Letter Queue (failed after N retries)
```

---

### 2.9 Async Worker Queue

**Responsibilities**:
- Long-running task processing
- Scheduled jobs
- Document processing
- Report generation
- Batch operations

**Job Types**:
```
Document Processing:
- Virus scan uploaded files
- Extract metadata
- Generate thumbnails
- Verify checksums

Report Generation:
- Transaction summaries
- Audit trail exports
- Analytics aggregation
- Retirement reports

Notifications:
- Batch email sending
- Reminder notifications
- Scheduled reports

Data Cleanup:
- Expired session cleanup
- Log archival
- Temporary file cleanup
```

**Architecture**:
```
Job Enqueue → Message Queue (Redis/RabbitMQ)
           → Worker Pool (auto-scaling)
           → Job Processing
           → Success/Failure Logging
           → Retry on Failure (exponential backoff)
           → Dead Letter Queue (persistent failures)
```

---

### 2.10 Audit & Compliance Layer

**Audit Log Schema**:
```json
{
  "audit_id": "uuid",
  "actor_id": "user_id",
  "actor_role": "operator|supplier|buyer|admin",
  "entity_type": "project|offer|order|inventory|retirement",
  "entity_id": "uuid",
  "action": "created|updated|approved|rejected|deleted",
  "before_state": { },
  "after_state": { },
  "timestamp": "2025-06-25T10:30:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "...",
  "request_id": "correlation-id"
}
```

**Critical Actions Requiring Audit**:
- Project submission/approval/rejection
- Offer creation/acceptance/rejection
- Contract signing
- Inventory creation/state change
- Order placement/payment/retirement
- User role changes
- Access to sensitive documents

---

## 3. Data Model Architecture

### 3.1 Database Schema (PostgreSQL)

```sql
-- Users & Authentication
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('supplier', 'buyer', 'operator', 'admin') NOT NULL,
  org_id UUID,
  status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
  email_verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Supplier Profiles
CREATE TABLE supplier_profiles (
  id UUID PRIMARY KEY,
  user_id UUID UNIQUE NOT NULL REFERENCES users(id),
  company_name VARCHAR(255),
  geography_region VARCHAR(100),
  land_size_hectares DECIMAL(10,2),
  land_ownership_type ENUM('owned', 'leased') NOT NULL,
  crop_types TEXT[], -- JSON array
  livestock_types TEXT[],
  payout_method ENUM('bank_transfer', 'check', 'payment_gateway') NOT NULL,
  payout_details JSONB, -- Bank account, check address, etc.
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
  id UUID PRIMARY KEY,
  supplier_id UUID NOT NULL REFERENCES supplier_profiles(id),
  methodology VARCHAR(100) NOT NULL,
  geography VARCHAR(255),
  crop_type VARCHAR(100),
  status ENUM('draft', 'submitted', 'in_review', 'needs_info', 'approved', 'rejected') DEFAULT 'draft',
  submission_date TIMESTAMP,
  submitted_by UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (supplier_id, status),
  INDEX (status)
);

-- Project Documents
CREATE TABLE project_documents (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  document_type ENUM('mrv_record', 'registry_evidence', 'land_ownership', 'other') NOT NULL,
  filename VARCHAR(255) NOT NULL,
  storage_uri VARCHAR(1024) NOT NULL, -- s3://bucket/path
  file_size_bytes INT,
  mime_type VARCHAR(100),
  checksum VARCHAR(255), -- SHA256
  uploaded_by UUID NOT NULL REFERENCES users(id),
  uploaded_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Reviews
CREATE TABLE reviews (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  reviewer_id UUID NOT NULL REFERENCES users(id),
  quality_score INT, -- 1-10
  readiness_score INT, -- 1-10
  risk_score INT, -- 1-10
  overall_score DECIMAL(5,2),
  decision ENUM('approved', 'rejected', 'needs_info', 'pending') DEFAULT 'pending',
  decision_reason TEXT,
  reviewed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (project_id),
  INDEX (decision)
);

-- Review Timeline (Status History)
CREATE TABLE review_timeline (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  status ENUM('new', 'in_review', 'needs_info', 'approved', 'rejected'),
  actor_id UUID NOT NULL REFERENCES users(id),
  changed_at TIMESTAMP DEFAULT NOW(),
  notes TEXT
);

-- Offers
CREATE TABLE offers (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  version INT DEFAULT 1,
  created_by UUID NOT NULL REFERENCES users(id),
  pricing_model JSONB NOT NULL, -- {type: 'per_unit'|'milestone', value, currency}
  fees_json JSONB, -- {brokerage: %, platform: %}
  payout_schedule_json JSONB, -- {type, milestones}
  delivery_expectations TEXT,
  liability_clauses TEXT,
  status ENUM('draft', 'sent', 'accepted', 'rejected', 'countered') DEFAULT 'draft',
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (project_id, status)
);

-- Contracts (Immutable)
CREATE TABLE contracts (
  id UUID PRIMARY KEY,
  offer_id UUID NOT NULL REFERENCES offers(id),
  signed_by UUID NOT NULL REFERENCES users(id),
  document_uri VARCHAR(1024) NOT NULL, -- s3://bucket/path (PDF)
  terms_snapshot JSONB NOT NULL, -- Complete snapshot of offer at signing
  signature_timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Inventory Lots
CREATE TABLE inventory_lots (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  issuance_type ENUM('issued', 'forward') NOT NULL,
  quantity_total DECIMAL(15,2) NOT NULL,
  quantity_available DECIMAL(15,2) NOT NULL,
  quantity_sold DECIMAL(15,2) DEFAULT 0,
  quantity_retired DECIMAL(15,2) DEFAULT 0,
  status ENUM('reserved', 'available', 'sold', 'retired') DEFAULT 'reserved',
  unit VARCHAR(50) DEFAULT 'tonnes',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (project_id, status)
);

-- Listings
CREATE TABLE listings (
  id UUID PRIMARY KEY,
  inventory_lot_id UUID NOT NULL REFERENCES inventory_lots(id),
  is_published BOOLEAN DEFAULT false,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  min_quantity DECIMAL(15,2),
  max_quantity DECIMAL(15,2),
  metadata_json JSONB, -- {co_benefits: [], vintage: 2024, registry: 'Gold Standard'}
  created_by UUID NOT NULL REFERENCES users(id),
  published_at TIMESTAMP,
  unpublished_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (inventory_lot_id, is_published),
  INDEX (is_published, created_at)
);

-- Orders
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  buyer_id UUID NOT NULL REFERENCES supplier_profiles(id), -- Buyer profile
  listing_id UUID NOT NULL REFERENCES listings(id),
  quantity DECIMAL(15,2) NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  total_price DECIMAL(15,2) NOT NULL,
  status ENUM('initiated', 'pending_payment', 'paid', 'transferred', 'retired') DEFAULT 'initiated',
  idempotency_key VARCHAR(255) UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (buyer_id, status),
  INDEX (listing_id),
  INDEX (status)
);

-- Payments
CREATE TABLE payments (
  id UUID PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES orders(id),
  provider_ref VARCHAR(255), -- Stripe/PayPal payment ID
  provider_name VARCHAR(50), -- 'stripe', 'paypal'
  amount DECIMAL(15,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status ENUM('initiated', 'pending', 'completed', 'failed', 'refunded') DEFAULT 'initiated',
  paid_at TIMESTAMP,
  metadata_json JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  INDEX (order_id, status)
);

-- Retirements
CREATE TABLE retirements (
  id UUID PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES orders(id),
  quantity DECIMAL(15,2) NOT NULL,
  retired_at TIMESTAMP NOT NULL,
  beneficiary_name VARCHAR(255),
  certificate_uri VARCHAR(1024), -- s3://bucket/path (PDF)
  certificate_number VARCHAR(255) UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  actor_id UUID NOT NULL REFERENCES users(id),
  entity_type VARCHAR(50) NOT NULL,
  entity_id UUID NOT NULL,
  action VARCHAR(50) NOT NULL,
  before_json JSONB,
  after_json JSONB,
  ip_address INET,
  user_agent TEXT,
  request_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX (entity_type, entity_id, created_at),
  INDEX (actor_id, created_at),
  INDEX (created_at)
);
```

---

## 4. Security Architecture

### 4.1 Authentication & Authorization

**Multi-Layer RBAC**:
```
User Role (supplier, buyer, operator, admin)
  ↓
Resource Ownership (user can only access own data by default)
  ↓
Action Permission (read, write, delete)
  ↓
Context Check (org/tenant isolation)
```

**Permission Matrix**:
```
Role          | Projects | Reviews | Offers | Orders | Inventory | Audit Logs
─────────────────────────────────────────────────────────────────────────────
Supplier      | RW(own)  | R(own)  | R      | R      | R(own)    | R(own)
Buyer         | -        | -       | -      | RW     | R         | R(own)
Operator      | R        | RWD     | RWD    | R      | RWD       | R
Admin         | RWD      | RWD     | RWD    | R      | RWD       | RWD
```

**Endpoint Protection**:
```
Every protected endpoint:
1. Extract JWT from Authorization header
2. Validate signature & expiry
3. Check user.status == 'active'
4. Verify action permission for role
5. Check resource ownership
6. Execute action
7. Log to audit_logs
```

### 4.2 Data Encryption

**In Transit**:
- All endpoints require HTTPS/TLS 1.2+
- API Gateway enforces TLS

**At Rest**:
- Database: PostgreSQL encryption or AWS RDS encryption
- Storage: S3 with AWS KMS encryption
- Sensitive fields (payment, payout details): AES-256 encryption at application level

**Sensitive Field Examples**:
- `users.password_hash` - bcrypt with salt
- `supplier_profiles.payout_details` - encrypted JSONB
- `payments.provider_ref` - encrypted (PCI compliance)

### 4.3 Audit & Compliance

**All Critical Actions Logged**:
- User login/logout
- Project submission/approval/rejection
- Offer creation/acceptance
- Contract signing
- Order placement/payment
- Inventory state changes
- Retirement recording
- Document access
- Role changes

**Immutable Audit Trail**:
- `audit_logs` table is append-only
- No UPDATE/DELETE on audit records
- Weekly export to cold storage (S3 Glacier)
- Retention: 7 years minimum

---

## 5. Performance & Scalability Architecture

### 5.1 Caching Strategy

**Redis Cache Layers**:
```
1. Session Cache (TTL: 24h)
   Key: session:{session_id}
   Value: {user_id, role, permissions, org_id}

2. User Token Cache (TTL: 15m)
   Key: token:{jwt_token_hash}
   Value: {valid: true/false}

3. Listing Cache (TTL: 5m)
   Key: listings:active
   Value: [listing objects for catalog search]

4. Rate Limit Counter (TTL: 1m)
   Key: rl:{user_id}:{endpoint}
   Value: {count, reset_at}
```

### 5.2 Database Indexing

**Query Performance Targets**:
- Catalog search (filter + sort): p95 <= 300ms
- Standard read endpoints: p95 <= 500ms
- List endpoints (paginated): p95 <= 200ms

**Key Indexes**:
```
projects:
  - (supplier_id, status)
  - (status, created_at DESC)

listings:
  - (inventory_lot_id, is_published)
  - (is_published, created_at DESC) for catalog search
  - geography, methodology, vintage as part of metadata_json

orders:
  - (buyer_id, status)
  - (listing_id)
  - (status, created_at)

audit_logs:
  - (entity_type, entity_id, created_at)
  - (actor_id, created_at)
  - (created_at) for archive queries

reviews:
  - (project_id)
  - (decision, created_at)
```

### 5.3 Horizontal Scaling

**API Servers**:
- Stateless REST API servers (auto-scale based on CPU/memory)
- Load balanced behind API Gateway
- Target: 250 req/s per server → scale to N servers

**Worker Queue**:
- Auto-scaling based on queue depth
- Min 2 workers, max 10 workers
- Dead letter queue for persistent failures

**Database**:
- Read replicas for reporting queries
- Write to primary, reads from replicas
- Connection pooling (PgBouncer)

---

## 6. Deployment Architecture

### 6.1 Infrastructure Stack

```
┌─────────────────────────────────────────────────┐
│           Cloud Provider (AWS/GCP/Azure)        │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  CDN (CloudFront)                        │  │
│  │  - Static assets                         │  │
│  │  - Geo-distribution                      │  │
│  └──────────────────────────────────────────┘  │
│                    │                            │
│  ┌──────────────────▼──────────────────────┐  │
│  │  Load Balancer (ALB)                    │  │
│  │  - HTTPS termination                    │  │
│  │  - Health checks                        │  │
│  └──────────────────┬──────────────────────┘  │
│                    │                            │
│  ┌─────────────────┼─────────────────┐        │
│  │                 │                 │        │
│  ▼                 ▼                 ▼        │
│ ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│ │  API-1   │   │  API-2   │   │  API-N   │  │
│ │(k8s pod) │   │(k8s pod) │   │(k8s pod) │  │
│ └──────────┘   └──────────┘   └──────────┘  │
│       │              │              │        │
│  ┌────▼──────────────▼──────────────▼───┐   │
│  │  RDS Primary (PostgreSQL)            │   │
│  │  - Write endpoint                    │   │
│  │  - Automated backups                 │   │
│  │  - Multi-AZ replication              │   │
│  └────┬──────────────────────────────────┘   │
│       │                                      │
│  ┌────▼──────────────────────────────────┐   │
│  │  RDS Replicas (Read-only)             │   │
│  │  - Analytics queries                  │   │
│  │  - Reporting workloads                │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  ┌───────────────────────────────────────┐   │
│  │  ElastiCache (Redis)                  │   │
│  │  - Sessions                           │   │
│  │  - Cache layer                        │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Worker Auto-Scaling Group             │  │
│  │  - Message queue consumers             │  │
│  │  - Background jobs                     │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  S3 Buckets                            │  │
│  │  - Documents storage                   │  │
│  │  - Backups/Archives                    │  │
│  │  - KMS encryption                      │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Message Queue (SQS/RabbitMQ)          │  │
│  │  - Job queue                           │  │
│  │  - Event stream                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Email Service (SES/SendGrid)          │  │
│  │  - Transactional emails                │  │
│  │  - Batch sends                         │  │
│  └────────────────────────────────────────┘  │
│                                              │
└─────────────────────────────────────────────────┘
```

### 6.2 Container Orchestration (Kubernetes)

```yaml
# API Service Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-service
  template:
    spec:
      containers:
      - name: api
        image: registry/api:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 7. Monitoring & Observability

### 7.1 Logging Architecture

**Structured Logging**:
```json
{
  "timestamp": "2025-06-25T10:30:00Z",
  "level": "INFO",
  "service": "api-service",
  "instance_id": "api-pod-1",
  "request_id": "req-123e4567",
  "user_id": "user-uuid",
  "action": "project_submitted",
  "entity_type": "project",
  "entity_id": "project-uuid",
  "duration_ms": 245,
  "status_code": 201,
  "message": "Project submitted successfully"
}
```

**Log Aggregation**: 
- Collect logs from all services → ELK (Elasticsearch, Logstash, Kibana) or CloudWatch
- Retention: 30 days in hot storage, 1 year in cold storage

### 7.2 Metrics & Dashboards

**Key Metrics**:
```
System Health:
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Request rate (req/s)
- Database connection pool usage
- Queue depth & processing time

Business Metrics:
- Daily active suppliers
- Daily active buyers
- Projects submitted (count, conversion rate)
- Approved projects (count, avg time in review)
- Total inventory listed (tonnes)
- Orders placed (count, value)
- Revenue (total, by supplier)
- Retirements (count, tonnes)

SLO Tracking:
- Availability: 99.5% monthly
- Catalog search p95: <= 300ms
- Standard read p95: <= 500ms
- Payment processing success rate: >= 99%
```

**Dashboard Tools**: Grafana, Datadog, or CloudWatch

### 7.3 Alerting

**Critical Alerts**:
- API error rate > 1%
- Database connection pool > 90%
- Queue processing lag > 5 minutes
- Payment service unavailable
- S3 replication lag
- Certificate generation failure

**Escalation**: PagerDuty integration with on-call rotation

---

## 8. Disaster Recovery & Continuity

### 8.1 Backup Strategy

**Database**:
- Automated daily snapshots (RDS)
- Continuous backup with 7-day retention
- Weekly snapshots to another region
- Point-in-time recovery capability

**Document Storage**:
- S3 versioning enabled
- Cross-region replication
- Lifecycle policy: 30 days hot → 1 year archive

**Configuration**:
- Infrastructure-as-Code (Terraform)
- Versioned in Git
- Disaster recovery playbook

### 8.2 RTO & RPO Targets

```
RTO (Recovery Time Objective):
- Data Loss: 1 hour (max 1 hour of data loss acceptable)
- Service Outage: 15 minutes (max 15 min downtime)

RPO (Recovery Point Objective):
- Database: 1 hour (hourly backups)
- Documents: 1 hour (replicated)
```

---

## 9. Development & Deployment Pipeline

### 9.1 CI/CD Pipeline

```
Developer
   ↓ push to feature branch
GitHub (pull request)
   ↓
Automated Tests:
  ├─ Unit tests (Jest/Pytest)
  ├─ Integration tests
  ├─ E2E tests (Cypress)
  ├─ Security scanning (SAST)
  └─ Code quality (SonarQube)
   ↓ (if all pass)
Code Review
   ↓ (if approved)
Merge to main
   ↓
Build Docker Image
   ↓
Push to Container Registry
   ↓
Deploy to Staging
   ↓ (after manual smoke tests)
Deploy to Production
   ↓ (with rolling deployment)
Monitor Health Metrics
```

### 9.2 Release Cadence

- **Bug fixes**: Deploy immediately (after CI/CD)
- **Features**: Weekly releases (Friday mornings for early detection)
- **Hotfixes**: On-demand (with emergency approval)

---

## 10. Migration & Rollout Strategy

### 10.1 Phased Rollout

**Phase 1: Supplier Onboarding** (Weeks 1-2)
- Core auth & RBAC
- Supplier registration & profile
- Project submission & document upload
- Internal operator review workflow

**Phase 2: Offers & Contracts** (Weeks 3-4)
- Offer generation & versioning
- Contract signing & storage
- Audit logging for contracts

**Phase 3: Inventory & Listing** (Weeks 5-6)
- Inventory lot creation
- Listing management
- Catalog search & filtering

**Phase 4: Buyer Commerce** (Weeks 7-8)
- Buyer registration
- Order creation & checkout
- Payment processing
- Transfer & retirement

**Phase 5: Reporting** (Weeks 9-10)
- Transaction history endpoints
- Audit reports
- Analytics dashboard

---

## 11. Open API Specification

**OpenAPI 3.0 Document** (to be generated):
- All 40+ endpoints documented
- Request/response schemas
- Authentication requirements
- Error codes & examples
- Rate limiting policies

---

## 12. Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| **Frontend** | React/Vue.js, TypeScript, TailwindCSS |
| **Backend** | Node.js/Python, Express/FastAPI |
| **Database** | PostgreSQL, Redis |
| **Storage** | AWS S3 with KMS |
| **Message Queue** | RabbitMQ or AWS SQS |
| **Email** | SendGrid or AWS SES |
| **Auth** | OAuth2, JWT |
| **Payment** | Stripe API |
| **Container** | Docker, Kubernetes |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus, Grafana, ELK |
| **Infrastructure** | AWS (or GCP/Azure) |

---

## 13. Success Criteria & KPIs

**Functional Success**:
- ✅ End-to-end workflow (submit → approve → offer → list → buy → retire)
- ✅ No data leakage across roles/tenants
- ✅ Inventory integrity (no overselling)
- ✅ Complete audit trail
- ✅ OpenAPI contract compliance

**Performance Success**:
- ✅ Catalog search p95 <= 300ms
- ✅ Standard read p95 <= 500ms
- ✅ 99.5% API availability

**Business Success**:
- ✅ 50+ suppliers onboarded
- ✅ 100+ projects submitted
- ✅ 10+ approved projects
- ✅ 500+ tonnes inventory listed
- ✅ 50+ orders completed
- ✅ $100K+ GMV (Gross Merchandise Volume)

---

**Document Version**: 1.0  
**Last Updated**: 2025-06-25  
**Status**: Ready for Implementation
