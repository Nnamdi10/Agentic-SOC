# Agentic SOC Platform — On-Premise Demo

An autonomous Security Operations Centre platform demonstrating agentic AI applied to enterprise cybersecurity. Built as a proof-of-concept for Fortune 500 SOC environments.

## What It Does

- **Autonomous SIEM monitoring** — continuously polls Wazuh for security alerts
- **ReAct reasoning loop** — local LLM (Llama 3.2 3B via Ollama) reasons through each alert step by step
- **Tool registry** — 8 security tools the agent can call: alert triage, asset lookup, vulnerability scanning, IP blocking, detection rule creation, incident reporting
- **Safety & action layer** — every action classified by blast radius (1–10). Actions ≥7 require human approval before execution
- **Rollback ledger** — every executed action logged with rollback command
- **Episodic memory** — agent stores past investigations and recalls relevant history for new alerts
- **SOC Dashboard** — real-time React UI showing agent reasoning, pending approvals, tool registry, rollback ledger

## Architecture
## Stack

| Component | Technology |
|-----------|-----------|
| SIEM | Wazuh 4.7.5 |
| LLM Runtime | Ollama + Llama 3.2 3B |
| Agent Orchestrator | Python / FastAPI |
| Dashboard | React (single-file, no build step) |
| Containerisation | Docker Compose |
| Attack Simulation | Custom bash scenarios |

## Running Locally

**Requirements:** Docker, Docker Compose, 8GB+ RAM

```bash
git clone https://github.com/YOUR_USERNAME/agentic-soc
cd agentic-soc
docker compose up -d
# Dashboard: http://localhost:3000
# Agent API: http://localhost:8000
```

## Demo Scenarios

The attack simulator automatically generates:
1. SSH brute force (47 attempts) → agent triages, queries asset inventory, proposes IP block
2. Port scan (1024 ports) → agent classifies as reconnaissance, creates detection rule
3. CVE-2021-41773 exploit attempt → agent scans target, surfaces CVEs, generates remediation plan
4. Suspicious outbound C2 beacon → agent investigates, escalates for human approval

## Key Design Decisions

- **Local LLM only** — no data leaves the perimeter. Demonstrates air-gapped deployment capability
- **Blast radius model** — mirrors enterprise change management. Low-risk actions auto-execute, high-risk require quorum approval
- **Reversibility first** — every action logs its rollback command before executing
- **Scalability path** — swap Llama 3B for 70B on GPU cluster, Qdrant for vector memory, Ansible for real remediation execution

## Author

Built as a demonstration of agentic AI applied to enterprise SOC operations.
