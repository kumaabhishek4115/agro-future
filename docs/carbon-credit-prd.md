# Product Requirements Document: Farmer Carbon Credit Marketplace

## 1. Purpose

Build a marketplace workflow that enables Agro Future to:
- purchase verified or verification-ready carbon credits from farmers and farmer aggregators;
- package, list, and sell those credits to corporate and institutional buyers; and
- create a transparent revenue model that rewards farmers fairly while preserving buyer trust.

## 2. Problem Statement

Farmers can generate carbon credits through regenerative and low-emission practices, but most struggle to access buyers, understand pricing, manage verification, and receive timely payment. On the demand side, buyers want high-quality agricultural credits with clear provenance, transparent impact data, and low procurement friction. Agro Future needs a product that bridges both sides of the market.

## 3. Product Goals

1. Make it simple for farmers to submit available credits or carbon projects for purchase.
2. Let Agro Future evaluate quality, pricing, and eligibility before buying from farmers.
3. Give buyers a trustworthy catalog of agricultural carbon credits with clear project metadata.
4. Support the full sell-side lifecycle: discovery, negotiation, purchase, transfer, retirement, and reporting.
5. Generate revenue through spread, service fees, or bundled marketplace services.

## 4. Users

### Supply-side users
- Individual farmers
- Farmer cooperatives and producer organizations
- Carbon project developers / aggregators
- Agro Future operations and carbon procurement teams

### Demand-side users
- Sustainability teams at food, retail, logistics, and manufacturing companies
- Carbon brokers and channel partners
- ESG / procurement teams seeking offsets or inset opportunities

## 5. Core User Stories

### Farmer / supplier
- As a farmer, I want to register my farm and practices so I can determine whether my project is eligible.
- As a farmer, I want to upload project, acreage, practice, and MRV information so Agro Future can assess my credits.
- As a farmer, I want a clear purchase offer showing price, fees, payment timing, and contract obligations.
- As a farmer, I want to track review, verification, and payout status.

### Buyer
- As a buyer, I want to browse credits by geography, crop, registry, methodology, price, and co-benefits.
- As a buyer, I want to review evidence of additionality, permanence, MRV, vintage, and retirement status.
- As a buyer, I want to reserve and purchase credits with clear transfer and retirement workflows.
- As a buyer, I want reporting artifacts for sustainability, audit, and stakeholder disclosure.

### Internal operations
- As an operator, I want to score incoming farmer supply by quality, readiness, and risk before making an offer.
- As an operator, I want to manage inventory, markup, buyer pricing, and retirement records.

## 6. Scope

### In scope
- Farmer onboarding and project intake
- Credit/project review and eligibility checks
- Purchase offer management
- Contract and payment status tracking
- Inventory management for purchased credits
- Buyer marketplace listings
- Quote, checkout, transfer, and retirement workflows
- Basic reporting for both sellers and buyers

### Out of scope for v1
- Building a new carbon registry
- Performing scientific verification in-house
- Tokenization or blockchain-native settlement
- Secondary-market trading between external third parties

## 7. Marketplace Workflow

### A. Buying carbon credits from farmers
1. **Onboard supplier**  
   Capture identity, geography, land size, crop/livestock type, ownership/lease rights, and bank/payment details.
2. **Collect project data**  
   Gather farming practices, start date, baseline, methodology, expected tonnes, supporting documents, and registry details if already issued.
3. **Run eligibility screening**  
   Check region, methodology fit, acreage thresholds, permanence requirements, overlap with existing programs, and fraud signals.
4. **Verify quality and readiness**  
   Confirm whether credits are already issued, pending issuance, or pre-issuance pipeline inventory. Review MRV documents and third-party verification evidence.
5. **Generate purchase offer**  
   Offer fixed price, floor-plus-share, or offtake-style pricing. Show deductions for verification, platform, and transaction fees where applicable.
6. **Execute contract**  
   Record exclusivity, delivery window, reversal liability, buffer deductions, and payment terms.
7. **Receive credits or delivery rights**  
   Transfer issued credits into Agro Future-managed inventory or reserve future issuance under contract.
8. **Pay supplier**  
   Trigger payout after transfer, milestone completion, or issuance confirmation.

### B. Selling credits to buyers
1. **Create inventory listing**  
   Publish credit details: project name, geography, practice, registry, methodology, vintage, tonnes, price, co-benefits, and risk notes.
2. **Support buyer discovery**  
   Enable filtering by project type, geography, certification, price range, and SDG/co-benefits.
3. **Provide trust artifacts**  
   Show MRV summaries, verification status, registry links, ownership chain, and retirement eligibility.
4. **Quote and reserve inventory**  
   Let buyers request quotes or directly reserve available tonnes.
5. **Complete transaction**  
   Process agreement, invoice/payment, transfer, and optional retirement on behalf of buyer.
6. **Deliver reporting**  
   Issue confirmation of transfer or retirement, project summary, and emissions claim support documents.

## 8. Functional Requirements

### Supply acquisition
- Supplier registration form with document upload
- Project intake workflow with draft and submitted states
- Operations review queue with approve / reject / request-more-info actions
- Offer creation with version history and acceptance status
- Payout status tracking

### Inventory and catalog
- Inventory records for issued and forward-supply credits
- Listing management with publish / unpublish controls
- Price management, margin controls, and availability tracking

### Buyer commerce
- Search and filterable marketplace catalog
- Detail page for each listing with quality and impact information
- Quote request or direct purchase flow
- Transfer and retirement workflow with downloadable confirmation

### Reporting and compliance
- Supplier transaction history
- Buyer purchase and retirement history
- Internal audit log for inventory ownership and status changes

## 9. Non-Functional Requirements

- **Transparency:** clear ownership chain, price visibility, and fee disclosure
- **Trust:** immutable transaction history and strong document retention
- **Scalability:** support many smallholder submissions and aggregated projects
- **Security:** protect farmer identity, contracts, and payment data
- **Usability:** low-friction onboarding for non-technical farm operators

## 10. Revenue Model

- Margin between farmer purchase price and buyer sale price
- Transaction fee per completed sale
- Premium services for MRV coordination, reporting, or buyer sourcing
- Long-term offtake agreements for enterprise buyers

## 11. Success Metrics

- Number of onboarded farmers / aggregators
- Tonnes of credits or forward supply submitted
- Approval rate of submitted supply
- Average time from submission to offer
- Average time from accepted offer to farmer payout
- Inventory sell-through rate
- Gross marketplace revenue and margin per tonne
- Buyer repeat purchase rate

## 12. Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Low-quality or fraudulent credits | Require registry evidence, verification documents, and internal risk screening |
| Farmer distrust of pricing | Show fee breakdowns, contract terms, and payout milestones clearly |
| Buyer concern about integrity | Surface methodology, MRV, permanence, and ownership-chain data on every listing |
| Delayed issuance | Distinguish issued inventory from forward supply and label delivery timelines clearly |
| Reversal / permanence issues | Track buffer deductions, liability clauses, and project monitoring requirements |

## 13. Suggested v1 Delivery Plan

### Phase 1: Supply intake
- Farmer signup
- Project submission
- Internal review dashboard

### Phase 2: Procurement operations
- Offer generation
- Contract and payout tracking
- Inventory creation

### Phase 3: Buyer marketplace
- Searchable listings
- Quote / checkout
- Transfer and retirement reporting

## 14. Open Questions

- Will Agro Future buy only already-issued credits, or also contract future issuance?
- Which registries and methodologies will be allowed in v1?
- Will pricing be fixed, negotiated, or auction-based?
- In which countries will farmer onboarding launch first?
- Will the marketplace support carbon insets in addition to offsets?
