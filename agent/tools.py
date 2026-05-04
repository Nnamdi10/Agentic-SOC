"""
Tool Registry — every capability the agent can call.
Each tool declares: name, description, blast_radius (1-10), reversible flag.
"""
import httpx
import json
import subprocess
from datetime import datetime
from typing import Any

WAZUH_BASE = "https://wazuh-manager:55000"
WAZUH_USER = "wazuh-wui"
WAZUH_PASS = "MyS3cr3tP4ssw0rd!"

# ── Auth helper ────────────────────────────────────────────────────────────────
async def wazuh_token() -> str:
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.post(
            f"{WAZUH_BASE}/security/user/authenticate",
            auth=(WAZUH_USER, WAZUH_PASS)
        )
        return r.json()["data"]["token"]

# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# Each tool is an async function + a metadata dict registered below.
# ══════════════════════════════════════════════════════════════════════════════

async def get_recent_alerts(limit: int = 10) -> dict:
    """Fetch the most recent SIEM alerts from Wazuh."""
    try:
        token = await wazuh_token()
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(
                f"{WAZUH_BASE}/alerts",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": limit, "sort": "-timestamp"}
            )
        alerts = r.json().get("data", {}).get("affected_items", [])
        return {"status": "ok", "count": len(alerts), "alerts": alerts}
    except Exception as e:
        # Wazuh not fully up yet — return simulated alerts for demo
        return _simulated_alerts(limit)

async def get_alert_detail(alert_id: str) -> dict:
    """Get full detail on a specific alert by ID."""
    try:
        token = await wazuh_token()
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(
                f"{WAZUH_BASE}/alerts",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": f"id={alert_id}"}
            )
        return r.json().get("data", {})
    except Exception as e:
        return {"status": "simulated", "alert_id": alert_id, "detail": "SSH brute force — 47 failed attempts from 192.168.100.50 against victim-node"}

async def query_asset_inventory(ip: str) -> dict:
    """Look up an IP in the asset inventory to understand what it is."""
    # In production this queries your CMDB. For demo, smart lookup.
    inventory = {
        "192.168.100.50": {"hostname": "attacker-sim", "role": "UNKNOWN EXTERNAL", "os": "Ubuntu", "criticality": "N/A", "owner": "UNKNOWN"},
        "192.168.100.10": {"hostname": "victim-node", "role": "Dev SSH Server", "os": "Ubuntu 18.04", "criticality": "medium", "owner": "infra-team"},
        "192.168.1.1":    {"hostname": "core-router", "role": "Network Infrastructure", "os": "Cisco IOS", "criticality": "critical", "owner": "network-team"},
    }
    result = inventory.get(ip, {"hostname": "unknown", "role": "unregistered asset", "criticality": "unknown", "owner": "unknown"})
    return {"status": "ok", "ip": ip, "asset": result}

async def block_ip(ip: str, reason: str) -> dict:
    """Block an IP address via iptables on the host. IRREVERSIBLE without explicit unblock."""
    try:
        result = subprocess.run(
            ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
            capture_output=True, text=True
        )
        return {
            "status": "ok",
            "action": "ip_blocked",
            "ip": ip,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "rollback_cmd": f"iptables -D INPUT -s {ip} -j DROP"
        }
    except Exception as e:
        # Demo mode — simulate the block
        return {
            "status": "simulated",
            "action": "ip_blocked",
            "ip": ip,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "rollback_cmd": f"iptables -D INPUT -s {ip} -j DROP"
        }

async def unblock_ip(ip: str) -> dict:
    """Remove an IP block — rollback action."""
    return {
        "status": "simulated",
        "action": "ip_unblocked",
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat()
    }

async def run_vulnerability_scan(target_ip: str) -> dict:
    """Run a basic vulnerability scan against a target IP."""
    # In production: trigger OpenVAS/Nessus. For demo: return realistic findings.
    return {
        "status": "ok",
        "target": target_ip,
        "scan_time": datetime.utcnow().isoformat(),
        "findings": [
            {"cve": "CVE-2023-38408", "service": "ssh", "port": 22, "severity": "HIGH", "cvss": 9.8, "description": "OpenSSH pre-auth RCE vulnerability", "fix": "Upgrade OpenSSH to 9.3p2+"},
            {"cve": "CVE-2021-41773", "service": "http", "port": 80, "severity": "CRITICAL", "cvss": 9.0, "description": "Apache path traversal / RCE", "fix": "Upgrade Apache to 2.4.51+"},
            {"cve": "CVE-2022-0847", "service": "kernel", "port": None, "severity": "HIGH", "cvss": 7.8, "description": "Dirty Pipe — local privilege escalation", "fix": "Kernel upgrade to 5.16.11+"},
        ]
    }

async def create_detection_rule(rule_name: str, condition: str, severity: str) -> dict:
    """Create a new Wazuh detection rule (tool builder capability)."""
    rule_xml = f"""
<group name="custom_rules">
  <rule id="100001" level="{8 if severity=='HIGH' else 5}">
    <description>{rule_name}</description>
    <match>{condition}</match>
    <group>custom_detection</group>
  </rule>
</group>"""
    return {
        "status": "simulated",
        "action": "detection_rule_created",
        "rule_name": rule_name,
        "rule_xml": rule_xml,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }

async def generate_incident_report(incident_summary: str, actions_taken: list) -> dict:
    """Generate a structured incident report."""
    report = {
        "report_id": f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "generated": datetime.utcnow().isoformat(),
        "summary": incident_summary,
        "timeline": actions_taken,
        "status": "resolved",
        "classification": "TLP:AMBER"
    }
    return {"status": "ok", "report": report}

# ── Simulated alerts for demo when Wazuh API isn't ready ──────────────────────
def _simulated_alerts(limit: int) -> dict:
    alerts = [
        {"id": "ALT001", "timestamp": datetime.utcnow().isoformat(), "rule": {"level": 10, "description": "SSH brute force attack detected", "id": "5712"}, "agent": {"name": "victim-node", "ip": "192.168.100.10"}, "data": {"srcip": "192.168.100.50", "attempt_count": 47}},
        {"id": "ALT002", "timestamp": datetime.utcnow().isoformat(), "rule": {"level": 8,  "description": "Port scan detected from external host", "id": "1002"}, "agent": {"name": "victim-node", "ip": "192.168.100.10"}, "data": {"srcip": "192.168.100.50", "ports_scanned": 1024}},
        {"id": "ALT003", "timestamp": datetime.utcnow().isoformat(), "rule": {"level": 7,  "description": "Suspicious outbound connection attempt", "id": "1003"}, "agent": {"name": "victim-node", "ip": "192.168.100.10"}, "data": {"srcip": "192.168.100.10", "dstip": "10.0.0.1"}},
    ]
    return {"status": "simulated", "count": min(limit, len(alerts)), "alerts": alerts[:limit]}

# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY — what the agent sees
# ══════════════════════════════════════════════════════════════════════════════
TOOL_REGISTRY = {
    "get_recent_alerts": {
        "fn": get_recent_alerts,
        "description": "Fetch recent security alerts from the SIEM. Use this first to understand what is happening.",
        "params": {"limit": "integer — number of alerts to fetch (default 10)"},
        "blast_radius": 1,
        "reversible": True,
    },
    "get_alert_detail": {
        "fn": get_alert_detail,
        "description": "Get full detail on a specific alert by its ID.",
        "params": {"alert_id": "string — the alert ID"},
        "blast_radius": 1,
        "reversible": True,
    },
    "query_asset_inventory": {
        "fn": query_asset_inventory,
        "description": "Look up an IP address in the asset inventory. Returns hostname, role, criticality, and owner.",
        "params": {"ip": "string — IP address to look up"},
        "blast_radius": 1,
        "reversible": True,
    },
    "run_vulnerability_scan": {
        "fn": run_vulnerability_scan,
        "description": "Run a vulnerability scan against a target IP. Returns CVEs, severity, and remediation steps.",
        "params": {"target_ip": "string — IP to scan"},
        "blast_radius": 3,
        "reversible": True,
    },
    "block_ip": {
        "fn": block_ip,
        "description": "Block an IP address at the network level. Use when confident of malicious activity.",
        "params": {"ip": "string — IP to block", "reason": "string — justification for the block"},
        "blast_radius": 7,
        "reversible": True,
    },
    "unblock_ip": {
        "fn": unblock_ip,
        "description": "Remove a network block on an IP address. Rollback action.",
        "params": {"ip": "string — IP to unblock"},
        "blast_radius": 6,
        "reversible": True,
    },
    "create_detection_rule": {
        "fn": create_detection_rule,
        "description": "Create a new detection rule in the SIEM to catch future occurrences of this attack pattern.",
        "params": {"rule_name": "string", "condition": "string — log pattern to match", "severity": "HIGH|MEDIUM|LOW"},
        "blast_radius": 5,
        "reversible": True,
    },
    "generate_incident_report": {
        "fn": generate_incident_report,
        "description": "Generate a structured incident report summarising the event and all actions taken.",
        "params": {"incident_summary": "string", "actions_taken": "list of action strings"},
        "blast_radius": 1,
        "reversible": True,
    },
}
