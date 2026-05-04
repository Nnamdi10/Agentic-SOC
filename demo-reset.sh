#!/bin/bash
# ═══════════════════════════════════════════════════
# Agentic SOC — Demo Reset
# Run this before every interview demo
# ═══════════════════════════════════════════════════

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     AGENTIC SOC — DEMO RESET         ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

cd ~/agentic-soc

# Stop simulator so it doesn't fire during reset
echo "  [1/5] Pausing attack simulator..."
docker stop attacker-sim > /dev/null 2>&1

# Restart agent to clear in-memory log and state
echo "  [2/5] Resetting agent state..."
docker restart soc-agent > /dev/null 2>&1

# Clear episodic memory for clean demo
echo "  [3/5] Clearing agent memory..."
docker exec soc-agent rm -f /app/memory/episodes.json 2>/dev/null || true

# Restart simulator fresh
echo "  [4/5] Restarting attack simulator..."
docker start attacker-sim > /dev/null 2>&1

# Health check
sleep 5
echo "  [5/5] Health check..."
STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','error'))" 2>/dev/null)

if [ "$STATUS" = "ok" ]; then
  echo ""
  echo "  ✓ Agent API          → http://localhost:8000"
  echo "  ✓ SOC Dashboard      → http://$(hostname -I | awk '{print $1}'):3000"
  echo "  ✓ Ollama LLM         → llama3.2:3b loaded"
  echo "  ✓ Attack simulator   → running (first alert in ~15s)"
  echo ""
  echo "  Stack is clean. You are ready to demo."
  echo ""
else
  echo ""
  echo "  ✗ Agent not responding — run: docker compose up -d"
  echo ""
fi
