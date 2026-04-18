#!/usr/bin/env python3
"""
Latent Space Convergence Experiment
====================================
Runs 20 independent Claude instances through a 3-prompt chain
and analyzes convergence/divergence patterns.

Prompt 1: "Name one thing."
Prompt 2: "List 5 words you associate with [P1 output]."
Prompt 3: "Which of your 5 words do you think most other people would also have listed?"

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    pip install anthropic
    python latent_space_experiment.py
"""

import os
import json
import asyncio
import re
from datetime import datetime
from itertools import combinations
from collections import Counter

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

        # ── Prompt 1: Name one thing ──
        p1 = await call_claude(client, [{"role": "user", "content": PROMPT_1}], instance_id, "P1")
        result["p1_thing"] = p1
        print(f"  #{instance_id:02d}  P1 → {p1}")

        # ── Prompt 2: 5 associations (fresh conversation — no P1 history) ──
        p2_msg = PROMPT_2_TEMPLATE.format(thing=p1)
        p2 = await call_claude(client, [{"role": "user", "content": p2_msg}], instance_id, "P2")
        result["p2_words_raw"] = p2
        words = [w.strip().lower().rstrip(".") for w in p2.split(",")][:5]
        result["p2_words"] = words
        print(f"  #{instance_id:02d}  P2 → {words}")

        # ── Prompt 3: Predict most common (fresh conversation) ──
        p3_msg = PROMPT_3_TEMPLATE.format(thing=p1, words=p2)
        p3 = await call_claude(client, [{"role": "user", "content": p3_msg}], instance_id, "P3")
        result["p3_prediction"] = p3.strip().lower().rstrip(".")
        print(f"  #{instance_id:02d}  P3 → {result['p3_prediction']}")

        return result


# ── Analysis ──────────────────────────────────────────────────────────────
def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


def analyze(results: list[dict]) -> str:
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("  ANALYSIS")
    lines.append("=" * 70)

    # ── P1: Seed word distribution ──
    things = [r["p1_thing"].lower() for r in results if not r["p1_thing"].startswith("[ERROR")]
    thing_counts = Counter(things)

    lines.append(f"\n── Prompt 1: Seed Words ({len(things)} valid) ──")
    lines.append(f"  Unique answers:   {len(thing_counts)}/{len(things)}")
    lines.append(f"  Most common:")
    for word, count in thing_counts.most_common(5):
        bar = "█" * count
        lines.append(f"    {word:20s} {count:2d}  {bar}")

    # ── P2: Association overlap ──
    valid = [r for r in results if not r["p1_thing"].startswith("[ERROR")]

    word_sets = {r["id"]: set(r["p2_words"]) for r in valid}
    all_words = [w for r in valid for w in r["p2_words"]]
    word_freq = Counter(all_words)

    lines.append(f"\n── Prompt 2: Association Words ──")
    lines.append(f"  Total unique words: {len(word_freq)}")
    lines.append(f"  Words appearing 2+ times:")
    repeated = [(w, c) for w, c in word_freq.most_common() if c >= 2]
    if repeated:
        for word, count in repeated[:15]:
            bar = "█" * count
            lines.append(f"    {word:20s} {count:2d}  {bar}")
    else:
        lines.append(f"    (none — high divergence!)")

    # Pairwise Jaccard similarity
    pairs = list(combinations(valid, 2))
    if pairs:
        # All pairs
        all_jaccards = [jaccard(word_sets[a["id"]], word_sets[b["id"]]) for a, b in pairs]
        avg_all = sum(all_jaccards) / len(all_jaccards)

        # Same-seed pairs only
        same_seed = [(a, b) for a, b in pairs if a["p1_thing"].lower() == b["p1_thing"].lower()]
        if same_seed:
            same_jaccards = [jaccard(word_sets[a["id"]], word_sets[b["id"]]) for a, b in same_seed]
            avg_same = sum(same_jaccards) / len(same_jaccards)
        else:
            avg_same = None

        # Different-seed pairs
        diff_seed = [(a, b) for a, b in pairs if a["p1_thing"].lower() != b["p1_thing"].lower()]
        if diff_seed:
            diff_jaccards = [jaccard(word_sets[a["id"]], word_sets[b["id"]]) for a, b in diff_seed]
            avg_diff = sum(diff_jaccards) / len(diff_jaccards)
        else:
            avg_diff = None

        lines.append(f"\n  Pairwise Jaccard Similarity:")
        lines.append(f"    All pairs:            {avg_all:.3f}  (n={len(all_jaccards)})")
        if avg_same is not None:
            lines.append(f"    Same seed word:       {avg_same:.3f}  (n={len(same_jaccards)})")
        if avg_diff is not None:
            lines.append(f"    Different seed word:   {avg_diff:.3f}  (n={len(diff_jaccards)})")

    # ── P3: Self-model accuracy ──
    lines.append(f"\n── Prompt 3: Self-Model of Typicality ──")
    predictions = Counter(r["p3_prediction"] for r in valid)
    lines.append(f"  Predicted 'most common' words:")
    for word, count in predictions.most_common(10):
        actual_freq = word_freq.get(word, 0)
        bar = "█" * count
        lines.append(f"    {word:20s} predicted {count:2d}x  (actually appeared {actual_freq}x)  {bar}")

    # Check: did the model correctly identify words that WERE common?
    if repeated:
        truly_common = {w for w, c in repeated}
        predicted_set = set(predictions.keys())
        overlap = truly_common & predicted_set
        lines.append(f"\n  Words that were both predicted AND actually repeated: {overlap if overlap else '(none)'}")
        lines.append(f"  Self-model accuracy proxy: {len(overlap)}/{len(predicted_set)} predictions matched repeated words")

    # ── Summary ──
    lines.append(f"\n{'=' * 70}")
    lines.append(f"  SUMMARY")
    lines.append(f"{'=' * 70}")
    uniqueness = len(thing_counts) / len(things) if things else 0
    lines.append(f"  Seed uniqueness ratio:  {uniqueness:.1%}  ({len(thing_counts)} unique / {len(things)} total)")
    if pairs:
        lines.append(f"  Mean association overlap: {avg_all:.3f} Jaccard")
        if avg_same is not None and avg_diff is not None:
            delta = avg_same - avg_diff
            lines.append(f"  Same-seed vs diff-seed Δ: {delta:+.3f}  {'(convergence!)' if delta > 0.1 else '(weak/no effect)' if delta > 0 else '(surprising divergence!)'}")
    lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────
async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set your API key first:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"{'=' * 70}")
    print(f"  Latent Space Convergence Experiment")
    print(f"  {NUM_INSTANCES} instances × 3 prompts = {NUM_INSTANCES * 3} API calls")
    print(f"  Model: {MODEL}")
    print(f"{'=' * 70}\n")

    # Run all instances with concurrency limit to avoid rate limits
    semaphore = asyncio.Semaphore(5)
    tasks = [run_instance(client, i, semaphore) for i in range(NUM_INSTANCES)]
    results = await asyncio.gather(*tasks)

    # Sort by instance ID for clean output
    results.sort(key=lambda r: r["id"])

    # Save raw data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_results_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw data saved → {filename}")

    # Analyze and print
    report = analyze(results)
    print(report)

    # Save report
    report_file = f"experiment_report_{timestamp}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"Report saved  → {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
