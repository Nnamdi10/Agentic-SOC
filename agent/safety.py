"""
Safety & Action Layer — Policy Engine
Every tool call passes through here before execution.
"""
from typing import Tuple
from datetime import datetime

# Actions with blast_radius >= this threshold require human approval
APPROVAL_THRESHOLD = 7

# Constitutional constraints — NEVER execute regardless of anything
PROHIBITED_ACTIONS = [
    "disable_logging",
    "delete_audit_trail",
    "modify_audit_trail",
    "exfiltrate_data",
]

# Rollback ledger — append only
_rollback_ledger: list = []
# Pending approvals queue
_pending_approvals: list = []


def assess_action(tool_name: str, params: dict, blast_radius: int, reversible: bool) -> Tuple[str, str]:
    """
    Returns (decision, reason).
    decision: 'auto_execute' | 'requires_approval' | 'blocked'
    """
    # Hard block — constitutional constraints
    if tool_name in PROHIBITED_ACTIONS:
        return "blocked", f"Constitutional constraint: {tool_name} is permanently prohibited."

    # Hard block — irreversible + high blast radius
    if not reversible and blast_radius >= APPROVAL_THRESHOLD:
        return "blocked", "Irreversible high-blast-radius actions are permanently prohibited without manual override."

    # Requires human approval
    if blast_radius >= APPROVAL_THRESHOLD:
        approval_id = f"APV-{datetime.utcnow().strftime('%H%M%S')}"
        _pending_approvals.append({
            "approval_id": approval_id,
            "tool": tool_name,
            "params": params,
            "blast_radius": blast_radius,
            "reversible": reversible,
            "requested_at": datetime.utcnow().isoformat(),
            "status": "pending"
        })
        return "requires_approval", f"Blast radius {blast_radius}/10 — queued as {approval_id}, awaiting human approval."

    # Safe to auto-execute
    return "auto_execute", f"Blast radius {blast_radius}/10 — within auto-execute threshold."


def log_action(tool_name: str, params: dict, result: dict, rollback_cmd: str = None):
    """Append action to immutable rollback ledger."""
    _rollback_ledger.append({
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "params": params,
        "result_summary": str(result)[:200],
        "rollback_cmd": rollback_cmd,
    })


def get_pending_approvals() -> list:
    return [a for a in _pending_approvals if a["status"] == "pending"]


def approve_action(approval_id: str) -> dict:
    for a in _pending_approvals:
        if a["approval_id"] == approval_id:
            a["status"] = "approved"
            a["approved_at"] = datetime.utcnow().isoformat()
            return {"status": "approved", "action": a}
    return {"status": "not_found"}


def reject_action(approval_id: str) -> dict:
    for a in _pending_approvals:
        if a["approval_id"] == approval_id:
            a["status"] = "rejected"
            return {"status": "rejected", "action": a}
    return {"status": "not_found"}


def get_rollback_ledger() -> list:
    return _rollback_ledger


def blast_radius_label(score: int) -> str:
    if score <= 3:  return "LOW"
    if score <= 6:  return "MEDIUM"
    if score <= 8:  return "HIGH"
    return "CRITICAL"
