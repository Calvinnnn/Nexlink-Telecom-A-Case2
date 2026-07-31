from typing import Dict, Any, List
import db

def generate_draft_outage_explanation_messages(account_id: int, ticket_id: int) -> List[Dict[str, str]]:
    """
    Generates messages for the draft_outage_explanation prompt template.
    Pulls live equipment diagnostics and ticket descriptions from the DB.
    """
    account = db.get_account_summary(account_id)
    if not account:
        account_info = f"Account #{account_id} (Customer name unavailable)"
    else:
        account_info = f"Customer: {account['customer_name']} (Account #{account_id}, Plan: {account['plan_name']})"
    
    ticket = db.get_ticket_by_id(ticket_id)
    if not ticket or ticket.get("account_id") != account_id:
        ticket_info = f"Ticket #{ticket_id} (No ticket details found for this account)"
    else:
        ticket_info = (
            f"Ticket #{ticket['ticket_id']} [{ticket['ticket_type'].upper()}]\n"
            f"Status: {ticket['status'].upper()}\n"
            f"Created: {ticket['created_at']}\n"
            f"Description: {ticket['description']}"
        )
    
    equipment = db.get_equipment_by_account(account_id)
    if not equipment:
        eq_info = "No registered equipment records found."
    else:
        eq_lines = []
        for eq in equipment:
            eq_lines.append(
                f"- Serial: {eq['serial_num']} | Model: {eq['model_type']} | Status: {eq['status'].upper()}\n"
                f"  Log: {eq['last_error_log'] or 'None'}"
            )
        eq_info = "\n".join(eq_lines)
    
    prompt_content = f"""You are a professional customer support representative for Nextlink ISP.
Draft a clear, empathetic, and professional message explaining a service outage or issue to the customer based on the following verified database records:

--- ACCOUNT DETAILS ---
{account_info}

--- SUPPORT TICKET DETAILS ---
{ticket_info}

--- EQUIPMENT DIAGNOSTIC STATUS ---
{eq_info}

--- INSTRUCTIONS FOR DRAFTING ---
1. Greet the customer by name.
2. Clearly explain the technical issue in plain language based on the equipment error log and ticket details.
3. State the current status of resolution (e.g. line sweep pending, dispatch scheduled, or line fault).
4. Reassure the customer and provide next steps.
"""

    return [
        {
            "role": "user",
            "content": prompt_content
        }
    ]
