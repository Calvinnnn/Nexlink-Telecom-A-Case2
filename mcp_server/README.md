# Nextlink ISP Support Assistant — MCP Server (`mcp_server/`)

This directory contains the production-ready Model Context Protocol (MCP) server for Nextlink, a fictional residential Internet Service Provider (ISP).

The server mediates all access to Nextlink's SQLite database (`nextlink.db`), ensuring LLM-based support assistants operate safely with strict identity verification, controlled write permissions, human-in-the-loop elicitation, and defensive schema design.

---

## 8 Protocol Concerns Implementation Mapping

| Protocol Concern | Trigger / Location | Implementation Details |
| --- | --- | --- |
| **1. Capability Negotiation** | `server.py` (`FastMCP` init) | Server declares tools (with `listChanged`), resources, prompts, elicitation, and sampling capabilities during `initialize`. |
| **2. Notifications (`tools/list_changed`)** | `auth.py`, `server.py` (`verify_account_identity`) | Session starts read-only. Calling `verify_account_identity` with a valid PIN marks session verified and fires `notifications/tools/list_changed` live without reconnecting. |
| **3. Elicitation (`elicitation/create`)** | `tools_write.py` (`apply_billing_credit`, `schedule_technician_dispatch`) | • `apply_billing_credit`: Elicits supervisor sign-off if credit > $25.00. Below $25.00 proceeds without elicitation.<br>• `schedule_technician_dispatch`: Always elicits human confirmation for $150 truck-roll cost. |
| **4. Resources** | `resources.py` (`nextlink://subscription-plans`, `nextlink://credit-policy`) | Exposes `SUBSCRIPTION_PLANS` DB table and `credit_policy.md` text document as resources (`resources/read`). |
| **5. Prompts** | `prompts.py` (`draft_outage_explanation`) | Parameterized prompt template (`account_id`, `ticket_id`) pulling equipment status and ticket info to draft customer responses. |
| **6. Sampling (`sampling/createMessage`)** | `tools_diagnostic.py` (`diagnose_equipment_issue`) | Reads raw technical log (`last_error_log`), then calls back through client host LLM (`sampling/createMessage`) to generate a plain-language root-cause summary. |
| **7. Transport Switch** | `server.py` (`--transport stdio` vs `--transport http`) | Started on `stdio` for local dev. Switched to `Streamable HTTP` for production deployment across multi-location call centers. |
| **8. Progress Tracking** | `tools_diagnostic.py` (`run_network_diagnostic_sweep`) | Slow multi-point diagnostic check reports real intermediate progress via `ctx.report_progress(progress, total, message)`. |

---

## Defensive Tool Design

Every write tool (`create_support_ticket`, `schedule_technician_dispatch`, `apply_billing_credit`) incorporates four defensive layers:
1. **Strict JSON Schema:** Explicit field types (`account_id >= 1`, `ticket_id >= 1`, `0.01 <= amount_usd <= 500.00`), required fields listed, `additionalProperties: false`, and rich parameter descriptions.
2. **Independent Server-Side Validation:** Input payload re-validated via `jsonschema.validate()` independent of MCP SDK declarations.
3. **Session-Level Handler Authorization:** Every write tool verifies that `verify_account_identity` was completed *for that specific account_id* in the active session.
4. **Database Integrity Verification:** Confirms target account and ticket exist in DB before mutation.

---

## Setup & Installation

### 1. Install Dependencies
```bash
cd mcp_server
pip install -r requirements.txt
```

### 2. Prepare Database
Ensure `nextlink.db` is built and seeded by running the teammate's script:
```bash
cd ../db
python reset_db.py
cd ../mcp_server
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `NEXTLINK_DB_PATH` points to `../db/nextlink.db`.

---

## Running the Server

### Stdio Transport (Local Development)
```bash
python server.py --transport stdio
```
Or using the built-in MCP Dev Inspector:
```bash
mcp dev server.py
```

### Streamable HTTP Transport (Production Demonstration Choice)
> **Why Streamable HTTP for final demo?** Nextlink operates multiple call-center locations with hundreds of concurrent customer support agents. A single local process over stdio cannot serve distributed agents. Streamable HTTP provides efficient, concurrent streaming endpoints for production host clients.

```bash
python server.py --transport http --host 0.0.0.0 --port 8000
```
Server endpoint: `http://localhost:8000/mcp`

---

## Repeatable Manual Test Suite (One Call Per Protocol Concern)

Use these fixed test inputs in MCP Inspector (`mcp dev server.py`) or client host to verify protocol functionality:

### 1. Capability Negotiation
- **Action:** Connect client. Inspect `initialize` response.
- **Expected Result:** Server returns capabilities including `tools` (listChanged=True), `resources`, `prompts`, `elicitation`, and `sampling`.

### 2. Read-Only Tool Lookup (No PIN required)
- **Call:** `get_account_summary(account_id=1)`
- **Expected Result:** Returns Sarah Branden's plan & address. PIN is **not** leaked.

### 3. Notifications & Identity Verification (`tools/list_changed`)
- **Call:** `verify_account_identity(account_id=2, account_pin=5678)`
- **Expected Result:** Validates Walter White's PIN (5678). Fires `notifications/tools/list_changed`. Session unlocks write tools (`create_support_ticket`, `schedule_technician_dispatch`, `apply_billing_credit`).

### 4. Elicitation — Controlled vs Uncontrolled Credit Threshold
- **Standard Case (≤ $25, No Elicitation):**
  - **Call:** `apply_billing_credit(account_id=2, ticket_id=2, amount_usd=15.00)`
  - **Expected Result:** Credit applied immediately since $15.00 ≤ $25.00 threshold.
- **Elevated Case (> $25, Elicitation Required):**
  - **Call:** `apply_billing_credit(account_id=2, ticket_id=2, amount_usd=50.00)`
  - **Expected Result:** Server pauses call and triggers `elicitation/create` requesting Supervisor approval. Applies credit only if supervisor approves.

### 5. Elicitation — Technician Dispatch
- **Call:** `schedule_technician_dispatch(account_id=2, description="Physical line fault after thunderstorm")`
- **Expected Result:** Server pauses call and triggers `elicitation/create` asking user to confirm the $150 truck-roll cost before creating the dispatch ticket.

### 6. Resources Read
- **Call:** Read resource `nextlink://subscription-plans`
- **Expected Result:** Returns Markdown table of Basic ($20), Standard ($35), and Premium ($60) plans.
- **Call:** Read resource `nextlink://credit-policy`
- **Expected Result:** Returns text of `credit_policy.md`.

### 7. Prompts Exposure
- **Call:** Get prompt `draft_outage_explanation(account_id=2, ticket_id=2)`
- **Expected Result:** Returns user prompt pre-populated with Walter White's account info, `SN-99X-002` error log, and ticket description.

### 8. Sampling (`sampling/createMessage`)
- **Call:** `diagnose_equipment_issue(serial_num="SN-99X-002")`
- **Expected Result:** Server fetches dense log (`CRIT_ERR: eth0 link down... HW_FAULT...`), issues `sampling/createMessage` to host LLM, and returns plain-language diagnosis: *"Physical line fault detected, likely storm damage, dispatch required."*

### 9. Progress Tracking
- **Call:** `run_network_diagnostic_sweep(account_id=2)`
- **Expected Result:** Live progress notifications emitted (`1/5`, `2/5`, `3/5`, `4/5`, `5/5`) before returning final sweep summary.
