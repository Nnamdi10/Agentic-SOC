"""
Memory Layer — episodic memory so the agent learns from past investigations.
Simple JSON-backed store for the demo. Production: swap for Qdrant vector DB.
"""
import json
import os
from datetime import datetime

MEMORY_FILE = "/app/memory/episodes.json"

def _load() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def _save(episodes: list):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(episodes, f, indent=2)

def store_episode(trigger: str, actions: list, outcome: str, lessons: str):
    """Store a completed investigation as an episodic memory."""
    episodes = _load()
    episodes.append({
        "id": f"EP-{len(episodes)+1:04d}",
        "timestamp": datetime.utcnow().isoformat(),
        "trigger": trigger,
        "actions": actions,
        "outcome": outcome,
        "lessons": lessons,
    })
    _save(episodes)

def recall_similar(trigger: str, limit: int = 3) -> list:
    """Retrieve past episodes relevant to the current trigger (keyword match for demo)."""
    episodes = _load()
    keywords = set(trigger.lower().split())
    scored = []
    for ep in episodes:
        ep_words = set(ep["trigger"].lower().split())
        score = len(keywords & ep_words)
        if score > 0:
            scored.append((score, ep))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ep for _, ep in scored[:limit]]

def get_all_episodes() -> list:
    return _load()
