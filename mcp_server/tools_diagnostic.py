import asyncio
import logging
from typing import Any, Dict, Optional

import db
from schemas import validate_tool_input

logger = logging.getLogger("nextlink_diagnostic")

async def handle_diagnose_equipment_issue(
    serial_num: str,
    ctx: Optional[Any] = None
) -> str:
    """
    Diagnoses equipment issue using Sampling (Protocol Concern #6).
    Reads dense last_error_log from DB, then calls sampling/createMessage back to the client's LLM
    to transform technical log entries into a plain-language root cause summary for agents.
    """
    validate_tool_input("diagnose_equipment_issue", {"serial_num": serial_num})
    
    device = db.get_equipment_by_serial(serial_num)
    if not device:
        return f"Error: Equipment with serial number '{serial_num}' not found."
    
    raw_log = device.get("last_error_log") or "No error logs available."
    model_type = device.get("model_type", "Unknown Model")
    status = device.get("status", "unknown")
    
    log_prompt = (
        f"You are a Senior Network Operations Technician at Nextlink ISP.\n"
        f"Analyze the following raw system error log from a {model_type} (Serial: {serial_num}, Status: {status}).\n\n"
        f"RAW ERROR LOG:\n{raw_log}\n\n"
        f"Task: Provide a concise (2-3 sentence) plain-language root cause summary for a customer support agent.\n"
        f"Explicitly state: 1) Physical/logical cause, 2) Impact, 3) Recommended action (e.g., dispatch required vs remote reboot)."
    )
    
    # Sampling / createMessage call through client host LLM
    if ctx and hasattr(ctx, "session") and hasattr(ctx.session, "create_message"):
        try:
            import mcp.types as types
            sample_messages = [
                types.SamplingMessage(
                    role="user",
                    content=types.TextContent(type="text", text=log_prompt)
                )
            ]
            
            logger.info(f"Issuing sampling/createMessage for serial {serial_num}")
            response = await ctx.session.create_message(
                messages=sample_messages,
                max_tokens=250,
                system_prompt="You are a helpful ISP network diagnostic expert.",
                temperature=0.2
            )
            
            if response and hasattr(response, "content"):
                if isinstance(response.content, types.TextContent):
                    diagnosis = response.content.text
                else:
                    diagnosis = str(response.content)
                return (
                    f"--- Automated Log Diagnosis (via Client LLM Sampling) ---\n"
                    f"Device Serial: {serial_num} ({model_type})\n"
                    f"Current Device Status: {status.upper()}\n\n"
                    f"Root Cause & Recommendations:\n{diagnosis}"
                )
        except Exception as e:
            logger.warning(f"Sampling call failed or fell back: {e}")
            # In case client does not support sampling or error occurs during testing
            fallback_diag = _heuristic_fallback_diagnosis(raw_log)
            return (
                f"--- Automated Log Diagnosis (Fallback - Client Sampling Unavailable: {e}) ---\n"
                f"Device Serial: {serial_num} ({model_type})\n"
                f"Current Status: {status.upper()}\n\n"
                f"Raw Log: {raw_log}\n"
                f"Heuristic Summary: {fallback_diag}"
            )
    
    # Fallback if context session create_message isn't available
    fallback_diag = _heuristic_fallback_diagnosis(raw_log)
    return (
        f"--- Automated Log Diagnosis (Stand-alone mode) ---\n"
        f"Device Serial: {serial_num} ({model_type})\n"
        f"Current Status: {status.upper()}\n\n"
        f"Raw Log: {raw_log}\n"
        f"Diagnostic Summary: {fallback_diag}"
    )

def _heuristic_fallback_diagnosis(raw_log: str) -> str:
    """Heuristic fallback summary if LLM sampling host is disconnected."""
    if "HW_FAULT" in raw_log or "loss of physical medium" in raw_log:
        return "Physical line fault detected (solid red LED / loss of physical medium). Likely physical cable or storm damage. Technician dispatch required."
    elif "SYS_OK" in raw_log:
        return "Equipment operating within normal parameters. No active error conditions detected."
    else:
        return f"Log entry recorded: {raw_log}. Further manual inspection advised."

async def handle_run_network_diagnostic_sweep(
    account_id: int,
    ctx: Optional[Any] = None
) -> str:
    """
    Runs a multi-stage network diagnostic sweep with real Progress Tracking (Protocol Concern #8).
    Reports real intermediate progress back to the host client at each diagnostic checkpoint.
    """
    validate_tool_input("run_network_diagnostic_sweep", {"account_id": account_id})
    
    if not db.account_exists(account_id):
        return f"Error: Account #{account_id} not found."
    
    checkpoints = [
        "1/5: Querying core routing node & gateway latency",
        "2/5: Inspecting physical fiber/coax link signal-to-noise ratio",
        "3/5: Pinging subscriber CPE modem / ONT interface",
        "4/5: Testing local LAN port states & packet loss rates",
        "5/5: Checking DNS resolution & upstream authentication logs"
    ]
    
    total = len(checkpoints)
    results = []
    
    for idx, stage_desc in enumerate(checkpoints, start=1):
        # Progress reporting via FastMCP / MCP SDK context
        if ctx and hasattr(ctx, "report_progress"):
            try:
                await ctx.report_progress(progress=idx, total=total, message=stage_desc)
                logger.info(f"Progress reported for Account #{account_id}: {idx}/{total}")
            except Exception as e:
                logger.warning(f"Could not report progress: {e}")
        
        # Simulate realistic multi-stage network test delay
        await asyncio.sleep(0.8)
        
        # Add test results
        if idx == 2 and account_id == 2:
            results.append(f"Stage {idx}: WARN - Fiber link optical power low (-28 dBm threshold breach)")
        elif idx == 3 and account_id == 2:
            results.append(f"Stage {idx}: FAIL - CPE Modem un-pingable / offline")
        else:
            results.append(f"Stage {idx}: OK - Passed ({stage_desc.split(': ')[1]})")
    
    sweep_summary = "\n".join(results)
    overall = "ACTION REQUIRED: Impaired physical link detected" if account_id == 2 else "ALL PASS: Network line nominal"
    
    return (
        f"--- Network Diagnostic Sweep Results for Account #{account_id} ---\n"
        f"Overall Status: {overall}\n\n"
        f"Stage Breakdown:\n{sweep_summary}"
    )
