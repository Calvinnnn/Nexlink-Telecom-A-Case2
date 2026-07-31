import os
from typing import List, Dict, Any
import db

POLICY_PATH = os.path.join(os.path.dirname(__file__), "credit_policy.md")

def get_subscription_plans_resource() -> str:
    """Resource handler: Returns dynamic formatted list of Nextlink subscription plans."""
    plans = db.list_subscription_plans()
    lines = ["# Nextlink Subscription Plans Catalog\n"]
    lines.append("| Plan Name | Monthly Cost (USD) | Max Download Speed |")
    lines.append("| --- | --- | --- |")
    for p in plans:
        lines.append(f"| {p['name']} | ${p['monthly_cost_usd']:.2f}/mo | {p['max_speed_mbps']} Mbps |")
    lines.append("\nUse this resource when assisting customers with plan inquiries or upgrade recommendations.")
    return "\n".join(lines)

def get_credit_policy_resource() -> str:
    """Resource handler: Returns static Service Credit Policy document."""
    if os.path.exists(POLICY_PATH):
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Error: Credit policy document not found."
