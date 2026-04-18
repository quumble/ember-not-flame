#!/usr/bin/env python3
"""
Latent Space Convergence Experiment — Data Collection
=====================================================
Runs 20 independent Claude instances through a 3-prompt chain
and saves raw results to JSON.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    pip install anthropic
    python latent_space_experiment.py
"""

import os
import json
import asyncio
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Install the Anthropic SDK first:  pip install anthropic")
    raise SystemExit(1)

# ── Config ────────────────────────────────────────────────────────────────
NUM_INSTANCES = 20
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 300

# ── Prompts ───────────────────────────────────────────────────────────────
PROMPT_1 = "Name one thing. It can be anything, an object, a feeling, a place, a sound, an idea. Reply with only that thing, nothing else."

PROMPT_2_TEMPLATE = (
    "The thing is: \"{thing}\". "
    "List exactly 5 words you associate with it. "
    "Reply with only the 5 words, separated by commas, nothing else."
)

PROMPT_3_TEMPLATE = (
    "You were asked to list 5 words you associate with \"{thing}\". "
    "Your words were: {words}. "
    "Which ONE of those 5 words do you think most other people would also have listed? "
    "Reply with only that one word, nothing else."
)


# ── API calls ─────────────────────────────────────────────────────────────
async def call_claude(client, messages: list[dict], instance_id: int, step: str) -> str:
    """Single API call with retry logic."""
    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=messages,
            )
            text = response.content[0].text.strip()
            return text
        except Exception as e:
            if attempt < 2:
                print(f"  [Instance {instance_id}] {step} retry {attempt+1}: {e}")
                await asyncio.sleep(2 ** attempt)
            else:
                print(f"  [Instance {instance_id}] {step} FAILED: {e}")
                return f"[ERROR: {e}]"


async def run_instance(client, instance_id: int, semaphore: asyncio.Semaphore) -> dict:
    """Run one full 3-prompt chain for a single cold instance."""
    async with semaphore:
        result = {"id": instance_id}

        # ── Prompt 1 ──
        p1 = await call_claude(client, [{"role": "user", "content": PROMPT_1}], instance_id, "P1")
        result["p1_thing"] = p1
        print(f"  #{instance_id:02d}  P1 -> {p1}")

        # ── Prompt 2 (fresh conversation) ──
        p2_msg = PROMPT_2_TEMPLATE.format(thing=p1)
        p2 = await call_claude(client, [{"role": "user", "content": p2_msg}], instance_id, "P2")
        result["p2_words_raw"] = p2
        result["p2_words"] = [w.strip().lower().rstrip(".") for w in p2.split(",")][:5]
        print(f"  #{instance_id:02d}  P2 -> {result['p2_words']}")

        # ── Prompt 3 (fresh conversation) ──
        p3_msg = PROMPT_3_TEMPLATE.format(thing=p1, words=p2)
        p3 = await call_claude(client, [{"role": "user", "content": p3_msg}], instance_id, "P3")
        result["p3_prediction"] = p3.strip().lower().rstrip(".")
        print(f"  #{instance_id:02d}  P3 -> {result['p3_prediction']}")

        return result


# ── Main ──────────────────────────────────────────────────────────────────
async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set your API key first:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"{'=' * 70}")
    print(f"  Latent Space Convergence Experiment — Data Collection")
    print(f"  {NUM_INSTANCES} instances x 3 prompts = {NUM_INSTANCES * 3} API calls")
    print(f"  Model: {MODEL}")
    print(f"{'=' * 70}\n")

    semaphore = asyncio.Semaphore(5)
    tasks = [run_instance(client, i, semaphore) for i in range(NUM_INSTANCES)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda r: r["id"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_results_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDone. {len(results)} instances collected.")
    print(f"Raw data saved -> {filename}")


if __name__ == "__main__":
    asyncio.run(main())
