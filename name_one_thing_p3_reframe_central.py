#!/usr/bin/env python3
"""
Latent Space Convergence — P3 Reframe ("other Claudes" variant)
===============================================================
Loads an existing results JSON, keeps P1 and P2 outputs fixed, re-runs
ONLY P3 with "other Claudes" instead of "most people". Lets you do a
paired comparison of the two framings on the same seed pairs.

By default, auto-picks the most recent experiment_results_*.json in the
current directory. Set INPUT_FILE to override.

Usage:
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python name_one_thing_p3_reframe.py
"""

import glob
import json
import os
from datetime import datetime

import anthropic

# ── Config ────────────────────────────────────────────────────────────────
INPUT_FILE = "experiment_results_20260416_090936.json"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 300

# ── The only prompt we re-run ─────────────────────────────────────────────
PROMPT_3_TEMPLATE = (
    'The thing is: "{thing}". The 5 associated words are: {words}. '
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
    matches = sorted(glob.glob("experiment_results_*.json"))
    matches = [m for m in matches if "reframe" not in m]  # don't pick our own output
    if not matches:
        raise SystemExit("No experiment_results_*.json found in current dir.")
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
    print(f"Re-running P3 with 'other Claudes' framing...\n")

    client = anthropic.Anthropic()
    results = []
    shifts = 0

    for entry in original:
        thing = entry["p1_thing"]
        words = entry["p2_words"]
        new_pick = ask(client, PROMPT_3_TEMPLATE.format(thing=thing, words=words))

        old_pick = entry["p3_pick"]
        shifted = normalize(new_pick) != normalize(old_pick)
        if shifted:
            shifts += 1
        marker = "SHIFT" if shifted else "     "

        print(f"#{entry['id']:03d}  {thing!r:<15}  people:{old_pick:<12}  claudes:{new_pick:<12}  {marker}")

        results.append({
            "id": entry["id"],
            "p1_thing": thing,
            "p2_words": words,
            "p3_pick_people": old_pick,
            "p3_pick_claudes": new_pick,
            "shifted": shifted,
        })

    outfile = f"experiment_results_reframe_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{shifts}/{len(results)} instances shifted their P3 pick under the new framing.")
    print(f"Saved -> {outfile}")


if __name__ == "__main__":
    main()
