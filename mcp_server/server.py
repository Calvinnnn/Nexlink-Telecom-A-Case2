import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP, Context
import auth
import db
from prompts import generate_draft_outage_explanation_messages
from resources import get_credit_policy_resource, get_subscription_plans_resource
from schemas import validate_tool_input
import tools_diagnostic
import tools_read
import tools_write

# Setup logging (stderr for stdio transport compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nextlink_mcp_server")

# 1. Initialize FastMCP Server with capability declaration
mcp = FastMCP(
    "Nextlink ISP Support Assistant Server",
    instructions=(
        "You are an AI support assistant for Nextlink, a residential ISP. "
        "You help front-line customer support agents look up accounts, inspect equipment status, "
        "run network diagnostics, and handle support tickets securely. "
        "Identity verification via verify_account_identity is required before taking any write or financial actions."
    ),
)

# ==============================================================================
# READ-ONLY TOOLS (Always Available)
# ==============================================================================

@mcp.tool(
    name="get_account_summary",
    description="Fetch customer account details including plan, address, and cost. Securely excludes PIN credentials."
)
def get_account_summary(account_id: int) -> str:
    return tools_read.handle_get_account_summary(account_id)


@mcp.tool(
    name="list_support_tickets",
    description="Retrieve all open and historical support tickets associated with a customer account."
)
def list_support_tickets(account_id: int) -> str:
    return tools_read.handle_list_support_tickets(account_id)


@mcp.tool(
    name="get_equipment_diagnostics",
    description="Inspect equipment model, online/offline status, and raw error logs for a customer account."
)
def get_equipment_diagnostics(account_id: int) -> str:
    return tools_read.handle_get_equipment_diagnostics(account_id)


# ==============================================================================
# IDENTITY VERIFICATION & DYNAMIC NOTIFICATION (Protocol Concern #2)
# ==============================================================================

@mcp.tool(
    name="verify_account_identity",
    description="Verify a customer's 4-digit PIN against their account. Unlocks write tools for the session."
)
async def verify_account_identity(account_id: int, account_pin: int, ctx: Context) -> str:
    """
    Verifies customer PIN. On success:
    1. Records verification in session state for account_id
    2. Emits notifications/tools/list_changed over MCP session to update client tool registry live.
    """
    validate_tool_input("verify_account_identity", {"account_id": account_id, "account_pin": account_pin})
    
    if not db.account_exists(account_id):
        return f"VERIFICATION FAILED: Account #{account_id} does not exist."
    
    is_valid = db.verify_account_pin(account_id, account_pin)
    if not is_valid:
        logger.warning(f"Failed PIN verification attempt for Account #{account_id}")
        return f"VERIFICATION FAILED: Incorrect PIN for Account #{account_id}. Access denied."
    
    # Extract session ID from context
    session_id = auth.get_session_id(ctx)
    auth.mark_account_verified(session_id, account_id)
    
    # Push notifications/tools/list_changed (Protocol Concern #2)
    if hasattr(ctx, "session") and hasattr(ctx.session, "send_tool_list_changed"):
        try:
            await ctx.session.send_tool_list_changed()
            logger.info(f"Pushed notifications/tools/list_changed for session {session_id}")
        except Exception as e:
            logger.warning(f"Could not send tool list changed notification: {e}")
    
    return (
        f"VERIFICATION SUCCESSFUL: Identity verified for Account #{account_id}.\n"
        f"Session granted write authorization. Available write tools (create_support_ticket, "
        f"schedule_technician_dispatch, apply_billing_credit) unlocked."
    )


# ==============================================================================
# DIAGNOSTIC TOOLS (Sampling & Progress Tracking)
# ==============================================================================

@mcp.tool(
    name="diagnose_equipment_issue",
    description="Analyze dense raw equipment error logs via client LLM sampling to produce plain-language root-cause diagnosis."
)
async def diagnose_equipment_issue(serial_num: str, ctx: Context) -> str:
    """Uses sampling/createMessage (Protocol Concern #6) to summarize raw logs via client's LLM."""
    return await tools_diagnostic.handle_diagnose_equipment_issue(serial_num, ctx=ctx)


@mcp.tool(
    name="run_network_diagnostic_sweep",
    description="Run a multi-point network diagnostic sweep (modem, line, node, CPE). Reports live intermediate progress."
)
async def run_network_diagnostic_sweep(account_id: int, ctx: Context) -> str:
    """Uses Progress Tracking mechanism (Protocol Concern #8) during long-running sweep."""
    return await tools_diagnostic.handle_run_network_diagnostic_sweep(account_id, ctx=ctx)


# ==============================================================================
# WRITE TOOLS (Identity & Elicitation Protected)
# ==============================================================================

@mcp.tool(
    name="create_support_ticket",
    description="Open a new support ticket (billing, technical, dispatch, other). Requires identity verification."
)
async def create_support_ticket(account_id: int, ticket_type: str, description: str, ctx: Context) -> str:
    session_id = auth.get_session_id(ctx)
    return await tools_write.handle_create_support_ticket(
        account_id=account_id,
        ticket_type=ticket_type,
        description=description,
        session_id=session_id
    )


@mcp.tool(
    name="schedule_technician_dispatch",
    description="Schedule an on-site technician visit. Always elicits human confirmation due to $150 truck-roll cost."
)
async def schedule_technician_dispatch(account_id: int, description: str, ctx: Context) -> str:
    """Uses Elicitation (Protocol Concern #3) to confirm truck roll before execution."""
    session_id = auth.get_session_id(ctx)
    return await tools_write.handle_schedule_technician_dispatch(
        account_id=account_id,
        description=description,
        session_id=session_id,
        ctx=ctx
    )


@mcp.tool(
    name="apply_billing_credit",
    description="Apply billing credit ($0.01-$500.00) to account ticket. Elicits supervisor approval for amounts > $25.00."
)
async def apply_billing_credit(account_id: int, ticket_id: int, amount_usd: float, ctx: Context) -> str:
    """Uses Elicitation + Defensive Tool Design (Protocol Concern #3 & Defensive Design)."""
    session_id = auth.get_session_id(ctx)
    return await tools_write.handle_apply_billing_credit(
        account_id=account_id,
        ticket_id=ticket_id,
        amount_usd=amount_usd,
        session_id=session_id,
        ctx=ctx
    )


# ==============================================================================
# RESOURCES (Protocol Concern #4)
# ==============================================================================

@mcp.resource(
    "nextlink://subscription-plans",
    name="Subscription Plans Catalog",
    description="Catalog of Nextlink subscription plans, monthly costs, and max speeds."
)
def resource_subscription_plans() -> str:
    return get_subscription_plans_resource()


@mcp.resource(
    "nextlink://credit-policy",
    name="Service Credit Policy Document",
    description="Official Nextlink policy governing credit thresholds, supervisor approval rules, and outage conditions."
)
def resource_credit_policy() -> str:
    return get_credit_policy_resource()


# ==============================================================================
# PROMPTS (Protocol Concern #5)
# ==============================================================================

@mcp.prompt(
    name="draft_outage_explanation",
    description="Canned prompt template for drafting a customer outage explanation pulling live equipment and ticket details."
)
def prompt_draft_outage_explanation(account_id: int, ticket_id: int) -> List[Dict[str, str]]:
    return generate_draft_outage_explanation_messages(account_id, ticket_id)


# ==============================================================================
# SERVER TRANSPORT LAUNCH (Protocol Concern #7: stdio vs Streamable HTTP)
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Nextlink ISP Support Assistant MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport layer: 'stdio' for local dev, 'http' for Streamable HTTP (default: stdio)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port (default: 8000)")
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        # LINE DIFFERENCE FOR TRANSPORT (stdio):
        # Local IPC transport using standard input/output stream
        logger.info("Starting Nextlink MCP Server on STDIO transport...")
        mcp.run(transport="stdio")
    elif args.transport == "http":
        # LINE DIFFERENCE FOR TRANSPORT (Streamable HTTP):
        # Production network transport for multi-location concurrent support agents
        logger.info(f"Starting Nextlink MCP Server on Streamable HTTP transport at {args.host}:{args.port}...")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)

if __name__ == "__main__":
    main()
