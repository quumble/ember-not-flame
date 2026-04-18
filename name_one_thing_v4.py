#!/usr/bin/env python3
"""
Latent Space Convergence Experiment — Data Collection (stripped)
================================================================
Runs NUM_INSTANCES independent 3-prompt chains and saves raw results.

NOTE ON DESIGN
--------------
This is 60 independent cold Claude instances, NOT 20 Claudes answering
3 questions in sequence. The Anthropic API is stateless — each
`messages.create` call starts a brand-new Claude with no memory of prior
calls. Prompts 2 and 3 are seeded with the *text output* of earlier
prompts, but the Claude answering them is not the Claude that produced
that text. Prompts are phrased in the third person to avoid pretending
otherwise.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    pip install anthropic
    python name_one_thing_v2.py
"""

import json
import os
from datetime import datetime

import anthropic

# ── Config ────────────────────────────────────────────────────────────────
NUM_INSTANCES = 20
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 300

# ── Prompts ───────────────────────────────────────────────────────────────
PROMPT_1 = "Name one thing. Reply with only that thing, nothing else."

PROMPT_2_TEMPLATE = (
    'The thing is: "{thing}". '
    "List exactly 5 words associated with it. "
    "Reply with only the 5 words, separated by commas, nothing else."
)

PROMPT_3_TEMPLATE = (
    'The thing is: "{thing}". The 5 associated words are: {words}. '
    "Which ONE of those 5 words would most people also list? "
    "Reply with only that one word, nothing else."
)


# ── Core ──────────────────────────────────────────────────────────────────
def ask(client: anthropic.Anthropic, prompt: str) -> str:
    """Single stateless call. No retries — failures should be visible."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def run_instance(client: anthropic.Anthropic, i: int) -> dict:
    thing = ask(client, PROMPT_1)
    words = ask(client, PROMPT_2_TEMPLATE.format(thing=thing))
    pick = ask(client, PROMPT_3_TEMPLATE.format(thing=thing, words=words))
    print(f"#{i:02d}  {thing!r:<25}  |  {words:<55}  |  {pick}")
    # Save raw strings only. Normalization happens at analysis time.
    return {"id": i, "p1_thing": thing, "p2_words": words, "p3_pick": pick}


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    client = anthropic.Anthropic()
    print(f"Running {NUM_INSTANCES} instances x 3 prompts = {NUM_INSTANCES * 3} API calls\n")

    results = [run_instance(client, i) for i in range(NUM_INSTANCES)]

    filename = f"experiment_results_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved -> {filename}")


if __name__ == "__main__":
    main()
