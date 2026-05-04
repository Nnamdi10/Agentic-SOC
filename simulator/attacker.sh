#!/bin/bash
# Agentic SOC — Attack Simulator
# Generates realistic attack sequences against victim-node

VICTIM="victim-node"
AGENT_API="http://soc-agent:8000"
LOG_PREFIX="[SIMULATOR]"

echo "$LOG_PREFIX Attack simulator starting in 15 seconds..."
sleep 15

# Install tools quietly
apt-get update -qq && apt-get install -y -qq nmap hydra curl netcat-openbsd 2>/dev/null

run_scenario() {
  local scenario=$1
  local alert=$2
  echo "$LOG_PREFIX ═══════════════════════════════════════"
  echo "$LOG_PREFIX SCENARIO: $scenario"
  echo "$LOG_PREFIX ═══════════════════════════════════════"

  # Notify agent via API
  curl -s -X POST "$AGENT_API/investigate" \
    -H "Content-Type: application/json" \
    -d "{\"alert\": \"$alert\", \"investigation_id\": \"AUTO-$(date +%s)\"}" \
    > /dev/null

  echo "$LOG_PREFIX Alert dispatched to agent"
}

# ── SCENARIO LOOP ─────────────────────────────────────────────────────────────
while true; do

  echo "$LOG_PREFIX Starting attack scenario cycle..."

  # Scenario 1: SSH Brute Force
  echo "$LOG_PREFIX [1/4] Simulating SSH brute force..."
  for i in $(seq 1 20); do
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=1 \
        -o PasswordAuthentication=yes \
        baduser@$VICTIM 2>/dev/null || true
    sleep 0.3
  done

  run_scenario "SSH_BRUTE_FORCE" \
    "SIEM ALERT [CRITICAL] — SSH brute force attack detected. 47 failed authentication attempts from 192.168.100.50 targeting victim-node (192.168.100.10) on port 22. Rule ID: 5712. Timeframe: 90 seconds."

  sleep 120

  # Scenario 2: Port Scan
  echo "$LOG_PREFIX [2/4] Simulating port scan..."
  nmap -T4 -F $VICTIM 2>/dev/null || true

  run_scenario "PORT_SCAN" \
    "SIEM ALERT [HIGH] — Network port scan detected. Host 192.168.100.50 scanned 1,024 ports on victim-node (192.168.100.10) within 30 seconds. Possible reconnaissance activity. Rule ID: 1002."

  sleep 120

  # Scenario 3: CVE Exploitation Attempt
  echo "$LOG_PREFIX [3/4] Simulating CVE exploitation attempt..."
  curl -s --max-time 3 "http://$VICTIM/.env" > /dev/null 2>&1 || true
  curl -s --max-time 3 "http://$VICTIM/admin" > /dev/null 2>&1 || true
  curl -s --max-time 3 "http://$VICTIM/../../../../etc/passwd" > /dev/null 2>&1 || true

  run_scenario "CVE_EXPLOIT_ATTEMPT" \
    "SIEM ALERT [CRITICAL] — CVE-2021-41773 exploitation attempt detected. Path traversal requests targeting Apache on victim-node (192.168.100.10). Attacker IP: 192.168.100.50. Requests: /../../../../etc/passwd, /.env, /admin. Rule ID: 31166."

  sleep 120

  # Scenario 4: Suspicious Outbound
  echo "$LOG_PREFIX [4/4] Simulating suspicious outbound connection..."
  nc -z -w 3 8.8.8.8 4444 2>/dev/null || true
  nc -z -w 3 8.8.8.8 1337 2>/dev/null || true

  run_scenario "SUSPICIOUS_OUTBOUND" \
    "SIEM ALERT [HIGH] — Suspicious outbound connection attempt. victim-node (192.168.100.10) attempted connections to external IPs on non-standard ports (4444, 1337). Possible C2 beacon or reverse shell. Rule ID: 1003."

  echo "$LOG_PREFIX Cycle complete. Waiting 3 minutes before next cycle..."
  sleep 180

done
