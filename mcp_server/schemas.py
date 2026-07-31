import jsonschema
from typing import Any, Dict

# Explicit JSON Schemas for each tool as per prompt requirements

VERIFY_ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account."
        },
        "account_pin": {
            "type": "integer",
            "minimum": 0,
            "maximum": 9999,
            "description": "Customer 4-digit security PIN for identity verification."
        }
    },
    "required": ["account_id", "account_pin"],
    "additionalProperties": False
}

GET_ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account."
        }
    },
    "required": ["account_id"],
    "additionalProperties": False
}

LIST_TICKETS_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account."
        }
    },
    "required": ["account_id"],
    "additionalProperties": False
}

GET_EQUIPMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account."
        }
    },
    "required": ["account_id"],
    "additionalProperties": False
}

DIAGNOSE_EQUIPMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "serial_num": {
            "type": "string",
            "minLength": 1,
            "description": "Unique hardware serial number of the modem/ONT device (e.g. SN-99X-002)."
        }
    },
    "required": ["serial_num"],
    "additionalProperties": False
}

NETWORK_SWEEP_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account to perform network sweep."
        }
    },
    "required": ["account_id"],
    "additionalProperties": False
}

CREATE_TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account."
        },
        "ticket_type": {
            "type": "string",
            "enum": ["billing", "technical", "dispatch", "other"],
            "description": "Category of the support ticket."
        },
        "description": {
            "type": "string",
            "minLength": 5,
            "description": "Detailed explanation of the customer issue or request."
        }
    },
    "required": ["account_id", "ticket_type", "description"],
    "additionalProperties": False
}

SCHEDULE_DISPATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account needing technician dispatch."
        },
        "description": {
            "type": "string",
            "minLength": 5,
            "description": "Detailed description of the technical issue requiring an on-site technician."
        }
    },
    "required": ["account_id", "description"],
    "additionalProperties": False
}

APPLY_CREDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier for the customer account receiving the credit."
        },
        "ticket_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Unique integer identifier of the open support ticket associated with this credit."
        },
        "amount_usd": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 500.00,
            "description": "Amount in USD to credit to the customer account ($0.01 to $500.00)."
        }
    },
    "required": ["account_id", "ticket_id", "amount_usd"],
    "additionalProperties": False
}

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "verify_account_identity": VERIFY_ACCOUNT_SCHEMA,
    "get_account_summary": GET_ACCOUNT_SCHEMA,
    "list_support_tickets": LIST_TICKETS_SCHEMA,
    "get_equipment_diagnostics": GET_EQUIPMENT_SCHEMA,
    "diagnose_equipment_issue": DIAGNOSE_EQUIPMENT_SCHEMA,
    "run_network_diagnostic_sweep": NETWORK_SWEEP_SCHEMA,
    "create_support_ticket": CREATE_TICKET_SCHEMA,
    "schedule_technician_dispatch": SCHEDULE_DISPATCH_SCHEMA,
    "apply_billing_credit": APPLY_CREDIT_SCHEMA,
}

def validate_tool_input(tool_name: str, arguments: Dict[str, Any]) -> None:
    """
    Performs server-side JSON Schema validation independent of MCP framework schema declarations.
    Raises ValueError with details if validation fails.
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return
    try:
        jsonschema.validate(instance=arguments, schema=schema)
    except jsonschema.ValidationError as err:
        raise ValueError(f"Server-side schema validation error for '{tool_name}': {err.message}")
