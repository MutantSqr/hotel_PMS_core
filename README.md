# Hotel PMS Core - State Assistant Engine

A Python-based domain orchestrator built with object-oriented design and defensive guardrails to model hotel operations, state management, reservation flows, and billing telemetry.

## System Architecture

* **Defensive Guardrails:** Input validation for check-in eligibility, out-of-order room locking, floor constraints (e.g., Presidential suites restricted to floor 15), and auto-calculated ledger balances.
* **State Management (`HotelAssistant`):** Encapsulates registration, room status transitions, vehicle linkages, and billing generation.

## Setup & Running Tests

1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/hotel-pms-core.git](https://github.com/YOUR_USERNAME/hotel-pms-core.git)
   cd hotel-pms-core