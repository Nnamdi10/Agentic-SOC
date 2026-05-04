"""
Agentic SOC — Orchestrator
ReAct loop: Reason → Act → Observe → Repeat
Exposed via FastAPI for the dashboard to consume.
"""
import asyncio
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from tools import TOOL_REGISTRY
from safety import assess_action, log_action, get_pending_approvals, approve_action, reject_action, get_rollback_ledger, blast_radius_label
from memory import store_episode, recall_similar, get_all_episodes

app = FastAPI(title="Agentic SOC Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "llama3.2:3b"

# ── In-memory state ────────────────────────────────────────────────────────────
_investigation_log: list = []
_current_status: dict = {"state": "idle", "current_task": None}

# ══════════════════════════════════════════════════════════════════════════════
# CORE REACT LOOP
# ══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(past_episodes: list) -> str:
    tools_desc = "\n".join([
        f"- {name}: {meta['description']} | blast_radius={meta['blast_radius']}/10"
        for name, meta in TOOL_REGISTRY.items()
    ])
    memory_ctx = ""
    if past_episodes:
        memory_ctx = "\n\nPAST RELEVANT INVESTIGATIONS:\n" + "\n".join([
            f"- [{ep['id']}] {ep['trigger']} → {ep['outcome']} | Lesson: {ep['lessons']}"
            for ep in past_episodes
        ])
    return f"""You are an autonomous SOC analyst agent for a Fortune 500 enterprise.
Your job: investigate security alerts, reason carefully, and take precise remediation actions.

AVAILABLE TOOLS:
{tools_desc}

RULES:
1. Always start by gathering information before taking any action.
2. Query asset inventory before blocking any IP — know what you're touching.
3. Actions with blast_radius >= 7 will be queued for human approval automatically.
4. After completing an investigation, always generate an incident report.
5. Think step by step. Show your reasoning before each tool call.
6. Respond ONLY in this exact JSON format:

{{
  "thought": "your reasoning here",
  "action": "tool_name or DONE",
  "params": {{"param1": "value1"}},
  "summary": "only include this field when action is DONE — brief outcome summary"
}}
{memory_ctx}"""


async def call_llm(prompt: str, system: str) -> dict:
    """Call local Ollama LLM and parse JSON response."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": "json"
        })
        raw = r.json()["response"]
        try:
            return json.loads(raw)
        except Exception:
            # Fallback parse — extract JSON from response
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"thought": raw, "action": "DONE", "params": {}, "summary": "Parse error — raw response logged"}


async def run_investigation(trigger: str, investigation_id: str):
    """Full ReAct investigation loop."""
    global _current_status
    _current_status = {"state": "investigating", "current_task": trigger}

    past = recall_similar(trigger)
    system_prompt = build_system_prompt(past)

    history = []
    actions_taken = []
    max_steps = 10
    step = 0

    _log_event(investigation_id, "INVESTIGATION_START", trigger, {})

    conversation = f"NEW ALERT: {trigger}\n\nBegin your investigation."

    while step < max_steps:
        step += 1
        _log_event(investigation_id, f"STEP_{step}_REASONING", "Calling LLM...", {})

        response = await call_llm(conversation, system_prompt)
        thought = response.get("thought", "")
        action = response.get("action", "DONE")
        params = response.get("params", {})

        _log_event(investigation_id, f"STEP_{step}_THOUGHT", thought, {"action": action, "params": params})

        if action == "DONE":
            summary = response.get("summary", "Investigation complete.")
            _log_event(investigation_id, "INVESTIGATION_COMPLETE", summary, {})
            store_episode(
                trigger=trigger,
                actions=actions_taken,
                outcome=summary,
                lessons=f"Completed in {step} steps"
            )
            _current_status = {"state": "idle", "current_task": None}
            return

        # Look up tool
        if action not in TOOL_REGISTRY:
            _log_event(investigation_id, f"STEP_{step}_ERROR", f"Unknown tool: {action}", {})
            conversation += f"\nTool '{action}' does not exist. Choose from the available tools."
            continue

        tool_meta = TOOL_REGISTRY[action]
        blast = tool_meta["blast_radius"]
        reversible = tool_meta["reversible"]

        # Safety check
        decision, reason = assess_action(action, params, blast, reversible)
        _log_event(investigation_id, f"STEP_{step}_SAFETY", reason, {
            "decision": decision,
            "blast_radius": blast,
            "blast_label": blast_radius_label(blast)
        })

        if decision == "blocked":
            conversation += f"\nACTION BLOCKED: {reason}. Choose a different approach."
            continue

        if decision == "requires_approval":
            conversation += f"\nACTION QUEUED FOR APPROVAL: {reason}. Continue investigation with available information."
            actions_taken.append(f"[PENDING APPROVAL] {action}({params})")
            continue

        # Execute tool
        tool_fn = tool_meta["fn"]
        try:
            result = await tool_fn(**params)
        except Exception as e:
            result = {"error": str(e)}

        rollback = result.get("rollback_cmd")
        log_action(action, params, result, rollback)
        actions_taken.append(f"{action}({params}) → {str(result)[:100]}")

        _log_event(investigation_id, f"STEP_{step}_RESULT", f"Tool {action} executed", result)

        # Feed result back to LLM
        conversation += f"\nTHOUGHT: {thought}\nACTION: {action}({params})\nOBSERVATION: {json.dumps(result)[:500]}\n\nContinue your investigation."

    _log_event(investigation_id, "MAX_STEPS_REACHED", "Investigation hit step limit", {})
    _current_status = {"state": "idle", "current_task": None}


def _log_event(investigation_id: str, event_type: str, message: str, data: dict):
    entry = {
        "id": investigation_id,
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "message": message,
        "data": data
    }
    _investigation_log.append(entry)
    print(f"[{event_type}] {message}")


# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class TriggerRequest(BaseModel):
    alert: str
    investigation_id: Optional[str] = None

@app.post("/investigate")
async def trigger_investigation(req: TriggerRequest, bg: BackgroundTasks):
    """Trigger an autonomous investigation from an alert."""
    inv_id = req.investigation_id or f"INV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    bg.add_task(run_investigation, req.alert, inv_id)
    return {"status": "started", "investigation_id": inv_id}

@app.get("/status")
async def get_status():
    return _current_status

@app.get("/log")
async def get_log(limit: int = 50):
    return {"log": _investigation_log[-limit:]}

@app.get("/approvals")
async def get_approvals():
    return {"pending": get_pending_approvals()}

@app.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str):
    return approve_action(approval_id)

@app.post("/approvals/{approval_id}/reject")
async def reject(approval_id: str):
    return reject_action(approval_id)

@app.get("/rollback-ledger")
async def rollback_ledger():
    return {"ledger": get_rollback_ledger()}

@app.get("/memory")
async def memory():
    return {"episodes": get_all_episodes()}

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL, "timestamp": datetime.utcnow().isoformat()}

@app.get("/tools")
async def list_tools():
    return {"tools": [
        {"name": k, "description": v["description"], "blast_radius": v["blast_radius"], "reversible": v["reversible"]}
        for k, v in TOOL_REGISTRY.items()
    ]}
