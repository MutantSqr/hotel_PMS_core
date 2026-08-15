# Hotel PMS Core

**A Python hotel property-management-system (PMS) domain engine focused on reservation integrity, room state, guest stays, billing, and night-audit guardrails.**

> Portfolio project demonstrating defensive business rules, object-oriented design, transaction-oriented billing, regression testing, and CI verification.

## Why This Project Exists

Hotel software has to protect real business rules. A reservation cannot overlap another reservation for the same room, an occupied room cannot be reassigned casually, and financial operations must not silently create incorrect balances.

Hotel PMS Core models those rules as explicit, testable domain logic rather than relying on informal application behavior.

## Core Capabilities

- **Reservation integrity**
  - Prevents overlapping reservations for the same room.
  - Supports reservation modification with the same availability rules used during creation.
  - Handles cancellation and room availability transitions.
- **Guest-stay lifecycle**
  - Guarded check-in and check-out flows.
  - Multi-guest reservations and accompanying guests.
  - Occupied-room protection and room-move availability checks.
- **Room inventory**
  - Room capacity and status validation.
  - Out-of-order / out-of-service guardrails.
  - Presidential-suite floor restriction.
- **Financial integrity**
  - Transaction-based folio/billing foundation.
  - Payment history instead of unrestricted balance mutation.
  - Credit and overpayment handling.
  - PM-account transfer support.
- **Night audit**
  - Guarded no-show processing.
  - Nightly room and tax posting.
  - Idempotency protections to prevent duplicate financial postings.
  - Audit-date and eligibility checks.

## Architecture

```text
Hotel PMS Core
│
├── Domain Models
│   ├── Guest
│   ├── Room
│   ├── Reservation
│   ├── Vehicle
│   └── Billing / Folio
│
├── Business Services
│   ├── Availability
│   ├── Reservation Modification
│   ├── Room Inventory
│   ├── Room Moves
│   ├── Nightly Posting
│   └── Night Audit
│
└── Verification
    ├── Unit / regression tests
    └── GitHub Actions CI
```

## Business Rules Demonstrated

The project intentionally emphasizes **fail-safe behavior**. Examples include:

- Two active reservations cannot claim the same room for overlapping dates.
- A room marked out of order cannot be reserved or checked into.
- A reservation cannot be checked in before its arrival date or after its departure date.
- A room cannot exceed its configured guest capacity.
- Outstanding balances require the appropriate settlement path during checkout.
- Nightly charges must be eligible for posting and must not be duplicated.
- Failed financial operations should leave the prior valid state unchanged.

## Quick Demo

The repository includes a small end-to-end demonstration covering room registration, guest registration, reservation creation, vehicle linkage, check-in, and checkout.

```bash
python main/main.py
```

The demo uses fictional data and does not connect to a real hotel, payment system, or guest database.

## Testing

The repository contains regression coverage for reservation availability, reservation modification, room inventory, room moves, check-in guardrails, multi-guest check-in, billing integrity, folio behavior, and night-audit posting.

Run the test suite locally with:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

GitHub Actions runs the test suite on pushes and pull requests targeting `main`.

## Project Status

**Current stage:** Core domain and financial guardrails are being hardened toward presentation-ready portfolio quality.

The project is intentionally **not presented as production-ready hotel software**. Security, authentication/authorization, persistent storage, API boundaries, deployment, compliance, and operational controls remain explicit future work before any real-world production deployment.

## Roadmap

- [x] Reservation overlap protection
- [x] Reservation modification availability checks
- [x] Guest check-in/check-out guardrails
- [x] Transaction-oriented billing foundation
- [x] Night-audit no-show guardrails
- [x] Nightly room/tax posting guardrails
- [ ] Security architecture and authorization boundary
- [ ] Persistent database layer
- [ ] API/application boundary
- [ ] Production deployment architecture
- [ ] Demonstration UI

## Portfolio Value

This project is intended to demonstrate practical software-engineering skills through a real business domain:

**Python → object-oriented design → domain modeling → business rules → defensive validation → financial integrity → automated testing → CI**

The next evolution is to expose the core through a secure application/API layer and connect it to automation and AI-assisted workflows.

## Author

**MutantSqr**

Built as part of an AI Software Engineering portfolio.
