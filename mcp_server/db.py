import os
import sqlite3
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "db", "nextlink.db")
)

def get_db_path() -> str:
    return os.environ.get("NEXTLINK_DB_PATH", DEFAULT_DB_PATH)

def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- Read Queries ---

def get_account_summary(account_id: int) -> Optional[Dict[str, Any]]:
    """Fetches account summary. IMPORTANT: Excludes account_pin to avoid credential leakage."""
    query = """
        SELECT 
            a.account_id,
            a.customer_name,
            a.address,
            p.plan_id,
            p.name as plan_name,
            p.monthly_cost_usd,
            p.max_speed_mbps
        FROM ACCOUNTS a
        JOIN SUBSCRIPTION_PLANS p ON a.plan_id = p.plan_id
        WHERE a.account_id = ?
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def verify_account_pin(account_id: int, pin: int) -> bool:
    """Verifies if the provided PIN matches the account PIN."""
    query = "SELECT account_pin FROM ACCOUNTS WHERE account_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        if not row:
            return False
        return int(row["account_pin"]) == pin

def list_support_tickets(account_id: int) -> List[Dict[str, Any]]:
    """Returns support tickets associated with an account."""
    query = """
        SELECT ticket_id, account_id, ticket_type, status, description, created_at
        FROM SUPPORT_TICKETS
        WHERE account_id = ?
        ORDER BY created_at DESC
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single ticket by ID."""
    query = """
        SELECT ticket_id, account_id, ticket_type, status, description, created_at
        FROM SUPPORT_TICKETS
        WHERE ticket_id = ?
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (ticket_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_equipment_by_account(account_id: int) -> List[Dict[str, Any]]:
    """Fetches equipment for an account."""
    query = """
        SELECT serial_num, account_id, model_type, status, last_error_log
        FROM EQUIPMENT
        WHERE account_id = ?
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_equipment_by_serial(serial_num: str) -> Optional[Dict[str, Any]]:
    """Fetches equipment details by serial number."""
    query = """
        SELECT serial_num, account_id, model_type, status, last_error_log
        FROM EQUIPMENT
        WHERE serial_num = ?
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (serial_num,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_subscription_plans() -> List[Dict[str, Any]]:
    """Retrieves all subscription plans for resource exposure."""
    query = """
        SELECT plan_id, name, monthly_cost_usd, max_speed_mbps
        FROM SUBSCRIPTION_PLANS
        ORDER BY monthly_cost_usd ASC
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, ())
        return [dict(row) for row in cursor.fetchall()]

def account_exists(account_id: int) -> bool:
    """Checks if an account exists."""
    query = "SELECT 1 FROM ACCOUNTS WHERE account_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id,))
        return cursor.fetchone() is not None

def ticket_exists_for_account(ticket_id: int, account_id: int) -> bool:
    """Checks if a ticket exists and belongs to the given account."""
    query = "SELECT 1 FROM SUPPORT_TICKETS WHERE ticket_id = ? AND account_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (ticket_id, account_id))
        return cursor.fetchone() is not None

# --- Write Operations ---

def create_support_ticket(account_id: int, ticket_type: str, description: str) -> Dict[str, Any]:
    """Creates a new support ticket."""
    query = """
        INSERT INTO SUPPORT_TICKETS (account_id, ticket_type, status, description)
        VALUES (?, ?, 'open', ?)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id, ticket_type, description))
        ticket_id = cursor.lastrowid
        conn.commit()
        return get_ticket_by_id(ticket_id)

def schedule_technician_dispatch(account_id: int, description: str) -> Dict[str, Any]:
    """Schedules a technician dispatch by opening a 'dispatch' support ticket."""
    query = """
        INSERT INTO SUPPORT_TICKETS (account_id, ticket_type, status, description)
        VALUES (?, 'dispatch', 'open', ?)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (account_id, description))
        ticket_id = cursor.lastrowid
        conn.commit()
        return get_ticket_by_id(ticket_id)

def apply_billing_credit(account_id: int, ticket_id: int, amount_usd: float) -> Dict[str, Any]:
    """Applies a billing credit note to an existing ticket."""
    update_desc = f" [CREDIT APPLIED: ${amount_usd:.2f}]"
    query = """
        UPDATE SUPPORT_TICKETS
        SET description = description || ?
        WHERE ticket_id = ? AND account_id = ?
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (update_desc, ticket_id, account_id))
        conn.commit()
        return get_ticket_by_id(ticket_id)
