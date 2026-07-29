from mcp.server.fastmcp import FastMCP
from schemas import AccountVerificationSchema
from db_utils import execute_query


mcp = FastMCP("Nextlink_Support_Agent")


@mcp.tool()
def verify_account(input_data: AccountVerificationSchema) -> str:
    query = "SELECT * FROM ACCOUNTS WHERE account_id = ? AND account_pin = ?"
    account = execute_query(query, (input_data.account_id, input_data.pin), fetch_one=True)

    if not account:
        return "AUTHORIZATION FAILED: Invalid Account ID or PIN. Do not proceed."

    equip_query = "SELECT serial_num, model_type FROM EQUIPMENT WHERE account_id = ?"
    equipment = execute_query(equip_query, (input_data.account_id,))

    return f"AUTH SUCCESS. Customer: {account['customer_name']}. Equipment: {equipment}"

#we can add more resources as files or in its separate folder, but for now we will keep it simple and add them here
@mcp.resource("policy://technician-dispatch")
def get_dispatch_policy() -> str:
    return "Nextlink Dispatch Policy: Dispatching technicians should be a last resort, only after all troubleshooting steps have been exhausted. Ensure to verify the account and equipment details before dispatching."

# TODO: Implement resources/read for Dispatch Policy, Routers LED colors and common errors, and Troubleshooting Steps.
# TODO: Implement prompts/list for Apology Email, Escalation Email, and Troubleshooting Steps.
# TODO: Implement tools/list_changed notification trigger

if __name__ == "__main__":
    import sys

    print("Starting Nextlink MCP Server", file=sys.stderr)
    mcp.run()