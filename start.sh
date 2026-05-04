#!/bin/bash
cd ~/agentic-soc
docker compose up -d
sleep 10
echo "Agentic SOC stack is up."
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
