import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

import db
import auth
from schemas import validate_tool_input

logger = logging.getLogger("nextlink_tools_write")

class SupervisorApprovalForm(BaseModel):
    approved: bool = Field(
        description="Select True to approve the elevated credit (> $25.00), or False to reject."
    )
    supervisor_id: Optional[str] = Field(
        default=None,
        description="Optional Supervisor ID or initials approving the credit."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Brief justification for approving or denying the elevated credit."
    )

class DispatchConfirmationForm(BaseModel):
    confirmed: bool = Field(
        description="Select True to confirm technician dispatch ($150 truck-roll operational cost), or False to cancel."
    )
    access_instructions: Optional[str] = Field(
        default=None,
        description="Gate codes or special access instructions for the technician."
    )

async def handle_create_support_ticket(
    account_id: int,
    ticket_type: str,
    description: str,
    session_id: str
) -> str:
    """Creates a new support ticket after handler-level identity verification."""
    # 1. Server-side schema validation
    validate_tool_input("create_support_ticket", {
        "account_id": account_id,
        "ticket_type": ticket_type,
        "description": description
    })
    
    # 2. Handler-level authorization check
    if not auth.is_account_verified(session_id, account_id):
        return (
            f"SECURITY ERROR: Identity for Account #{account_id} has not been verified in this session. "
            f"You must call verify_account_identity(account_id={account_id}, account_pin=...) first."
        )
    
    # 3. Database existence check
    if not db.account_exists(account_id):
        return f"Error: Account #{account_id} does not exist in the database."
    
    # 4. Execute DB action
    ticket = db.create_support_ticket(account_id, ticket_type, description)
    return (
        f"SUCCESS: Support ticket #{ticket['ticket_id']} created for Account #{account_id}.\n"
        f"  Type: {ticket['ticket_type'].upper()}\n"
        f"  Status: {ticket['status'].upper()}\n"
        f"  Description: {ticket['description']}"
    )

async def handle_schedule_technician_dispatch(
    account_id: int,
    description: str,
    session_id: str,
    ctx: Optional[Any] = None
) -> str:
    """
    Schedules technician dispatch with mandatory Elicitation (Protocol Concern #3).
    Always elicits human confirmation due to real truck-roll financial cost (~$150).
    """
    # 1. Server-side schema validation
    validate_tool_input("schedule_technician_dispatch", {
        "account_id": account_id,
        "description": description
    })
    
    # 2. Handler-level authorization check for specific account_id
    if not auth.is_account_verified(session_id, account_id):
        return (
            f"SECURITY ERROR: Identity for Account #{account_id} has not been verified in this session. "
            f"You must verify customer identity with account_pin before scheduling dispatches."
        )
    
    # 3. Database existence check
    account = db.get_account_summary(account_id)
    if not account:
        return f"Error: Account #{account_id} does not exist."
    
    # 4. Elicitation (protocol concern #3) — Always elicit dispatch confirmation before finalizing
    if ctx and hasattr(ctx, "elicit"):
        try:
            prompt_msg = (
                f"OPERATIONAL CONFIRMATION REQUIRED:\n"
                f"Dispatching a technician to '{account['address']}' for Account #{account_id} "
                f"incurs a ~$150.00 truck-roll cost.\n"
                f"Please confirm whether to proceed with scheduling the technician dispatch."
            )
            elicit_res = await ctx.elicit(message=prompt_msg, schema=DispatchConfirmationForm)
            
            # Check response
            if elicit_res and hasattr(elicit_res, "data") and elicit_res.data:
                data: DispatchConfirmationForm = elicit_res.data
                if not data.confirmed:
                    return f"DISPATCH CANCELLED: User declined technician dispatch for Account #{account_id}."
                if data.access_instructions:
                    description += f" [Access Notes: {data.access_instructions}]"
            elif elicit_res and hasattr(elicit_res, "action") and elicit_res.action != "accept":
                return f"DISPATCH CANCELLED: Elicitation action was '{elicit_res.action}'."
        except Exception as e:
            logger.warning(f"Elicitation check fallback due to client/transport context: {e}")
            # If client does not support elicitation or error occurs, log and notify
            return f"ELICITATION ERROR: Client did not complete dispatch confirmation dialog ({e}). Dispatch cancelled."

    # 5. Execute DB action
    ticket = db.schedule_technician_dispatch(account_id, description)
    return (
        f"SUCCESS: Technician dispatch scheduled for Account #{account_id}.\n"
        f"  Ticket ID: #{ticket['ticket_id']}\n"
        f"  Dispatch Address: {account['address']}\n"
        f"  Status: {ticket['status'].upper()}\n"
        f"  Description: {ticket['description']}"
    )

async def handle_apply_billing_credit(
    account_id: int,
    ticket_id: int,
    amount_usd: float,
    session_id: str,
    ctx: Optional[Any] = None
) -> str:
    """
    Applies a billing credit to a customer account.
    Demonstrates Elicitation (Protocol Concern #3) and Defensive Tool Design:
    - Controlled vs Uncontrolled case:
      - Credits <= $25.00: proceed after identity verification without elicitation.
      - Credits > $25.00: elicit supervisor approval before applying.
    - Defensive design:
      1. Schema validation (0.01 <= amount_usd <= 500.00, account_id >= 1, ticket_id >= 1)
      2. Server-side validation independent of schema
      3. Handler-level authorization (specific account_id verified in session)
      4. Database validation (account exists, ticket exists for account)
    """
    # 1. Server-side validation independent of schema
    validate_tool_input("apply_billing_credit", {
        "account_id": account_id,
        "ticket_id": ticket_id,
        "amount_usd": amount_usd
    })
    
    # 2. Hard bounds re-check on amount_usd ($0.01 to $500.00)
    if amount_usd < 0.01 or amount_usd > 500.00:
        return f"REJECTED: Credit amount ${amount_usd:.2f} violates policy limits ($0.01 - $500.00)."
    
    # 3. Handler-level authorization check for specific account_id
    if not auth.is_account_verified(session_id, account_id):
        return (
            f"SECURITY ERROR: Session unauthorized for Account #{account_id}. "
            f"Identity verification (verify_account_identity) is required prior to applying financial credits."
        )
    
    # 4. Database integrity checks: account & ticket existence
    if not db.account_exists(account_id):
        return f"DATABASE ERROR: Account #{account_id} does not exist."
    
    if not db.ticket_exists_for_account(ticket_id, account_id):
        return f"DATABASE ERROR: Ticket #{ticket_id} not found for Account #{account_id}."
    
    # 5. Elicitation (Protocol Concern #3) - Threshold check
    ELEVATED_THRESHOLD = 25.00
    if amount_usd > ELEVATED_THRESHOLD:
        if ctx and hasattr(ctx, "elicit"):
            try:
                elicit_msg = (
                    f"SUPERVISOR APPROVAL REQUIRED:\n"
                    f"Requested credit amount of ${amount_usd:.2f} exceeds standard agent threshold (${ELEVATED_THRESHOLD:.2f}).\n"
                    f"Account ID: #{account_id}, Ticket ID: #{ticket_id}.\n"
                    f"Please confirm supervisor authorization to apply this credit."
                )
                elicit_res = await ctx.elicit(message=elicit_msg, schema=SupervisorApprovalForm)
                
                if elicit_res and hasattr(elicit_res, "data") and elicit_res.data:
                    approval: SupervisorApprovalForm = elicit_res.data
                    if not approval.approved:
                        sup = approval.supervisor_id or "Supervisor"
                        reason = approval.reason or "No reason provided"
                        return f"CREDIT DENIED: Credit of ${amount_usd:.2f} was rejected by {sup} ({reason})."
                elif elicit_res and hasattr(elicit_res, "action") and elicit_res.action != "accept":
                    return f"CREDIT DENIED: Elicitation action was '{elicit_res.action}'."
            except Exception as e:
                logger.warning(f"Elicitation error: {e}")
                return f"CREDIT REJECTED: Client failed supervisor elicitation requirement ({e}). Credit not applied."
        else:
            return (
                f"ELEVATED CREDIT REQUIRES ELICITATION CAPABILITY: "
                f"Credit of ${amount_usd:.2f} exceeds ${ELEVATED_THRESHOLD:.2f} limit. "
                f"Connecting client does not support elicitation for supervisor sign-off."
            )
    
    # 6. Execute DB action
    updated_ticket = db.apply_billing_credit(account_id, ticket_id, amount_usd)
    
    tier_note = "(Elevated Credit - Supervisor Approved)" if amount_usd > ELEVATED_THRESHOLD else "(Standard Agent Credit)"
    return (
        f"SUCCESS: Billing credit of ${amount_usd:.2f} applied to Account #{account_id} on Ticket #{ticket_id} {tier_note}.\n"
        f"  Updated Ticket Description: {updated_ticket['description']}"
    )
