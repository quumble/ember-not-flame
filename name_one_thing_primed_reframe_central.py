#!/usr/bin/env python3
"""
Latent Space Convergence — PRIMED P3 Reframe ("other Claudes" variant)
======================================================================
Companion to name_one_thing_p3_reframe.py, but operates on the PRIMED
baseline (experiment_results_primed_*.json from name_one_thing_v6.py)
rather than the stripped baseline.

Loads the primed run's P1 and P2 outputs and re-runs ONLY P3 with
"other Claudes" instead of "most other people". Fills the final cell
of the 2x2 design:

    primed prompt + "most people" frame   <- already ran (v6 baseline)
    primed prompt + "other Claudes" frame <- this script
    stripped prompt + "most people" frame <- already ran
    stripped prompt + "other Claudes" frame <- already ran

By default, auto-picks the most recent experiment_results_primed_*.json.
Set INPUT_FILE to override.

Usage:
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python name_one_thing_primed_reframe.py
"""

import glob
import json
import os
from datetime import datetime

import anthropic

# ── Config ────────────────────────────────────────────────────────────────
INPUT_FILE = None  # None = auto-pick most recent experiment_results_primed_*.json
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 300

# ── The reframed P3 prompt (key change: "other Claudes" not "most other people") ──
# Matches v6's second-person framing for consistency with the primed baseline.
PROMPT_3_TEMPLATE = (
    'You were asked to list 5 words you associate with "{thing}". '
    "Your words were: {words}. "
    "Which ONE of those 5 words is most central to the concept? "
    "Reply with only that one word, nothing else."
)


def ask(client: anthropic.Anthropic, prompt: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def find_input_file() -> str:
    if INPUT_FILE:
        return INPUT_FILE
    matches = sorted(glob.glob("experiment_results_primed_*.json"))
    matches = [m for m in matches if "reframe" not in m]  # don't pick our own output
    if not matches:
        raise SystemExit(
            "No experiment_results_primed_*.json found in current dir.\n"
            "Run name_one_thing_v6.py first to produce the primed baseline."
        )
    return matches[-1]


def normalize(s: str) -> str:
    return s.lower().strip().rstrip(".")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    infile = find_input_file()
    with open(infile) as f:
        original = json.load(f)

    print(f"Loaded {len(original)} instances from {infile}")
    print(f"Re-running P3 with 'other Claudes' framing (sequential)...\n")

    client = anthropic.Anthropic()
    results = []
    shifts = 0

    for entry in original:
        thing = entry["p1_thing"]
        # v6 stores both a raw string (p2_words_raw) and a parsed list (p2_words).
        # We want the string for the P3 prompt.
        words_str = entry.get("p2_words_raw") or ", ".join(entry["p2_words"])
        old_pick = entry["p3_prediction"]

        new_pick = ask(client, PROMPT_3_TEMPLATE.format(thing=thing, words=words_str))

        shifted = normalize(new_pick) != normalize(old_pick)
        if shifted:
            shifts += 1
        marker = "SHIFT" if shifted else "     "

        print(f"#{entry['id']:03d}  {thing!r:<15}  people:{old_pick:<14}  claudes:{new_pick:<14}  {marker}")

        results.append({
            "id": entry["id"],
            "p1_thing": thing,
            "p2_words_raw": words_str,
            "p3_pick_people": old_pick,
            "p3_pick_claudes": new_pick,
            "shifted": shifted,
        })

    outfile = f"experiment_results_primed_reframe_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{shifts}/{len(results)} instances shifted their P3 pick under the Claude frame.")
    print(f"Saved -> {outfile}")


if __name__ == "__main__":
    main()
