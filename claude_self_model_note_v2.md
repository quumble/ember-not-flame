# A Small Experiment on Claude's Self-Model (v2)

Bo and Claude (Opus 4.7)
April 2026

## Summary

When cold Claude Sonnet 4.6 is given a word-association chain and asked "which of these words would *most people* also list?" vs. "which would *other Claudes* also list?", picks shift in a consistent direction across three seed concepts: actions and sensations (sit, wet) give way to objects and categories (seat, furniture, umbrella) under the Claude framing. Adding a third framing — "which is *most central to the concept*?" — was intended to test whether Claude models "other Claudes" as approximately dictionary-neutral conceptual centrality. The result is a clean partial: central aligns with claudes for "chair," but diverges sharply for "rain," where claudes favors the human-relevant artifact (umbrella, 92/100) and central favors the natural essence (wet when available, clouds otherwise). Claude's self-model is not just conceptual centrality. It looks closer to *pragmatic helpfulness* — the best one-word answer for a reader — which sometimes coincides with centrality and sometimes doesn't.

## Method

Three prompts. Each prompt goes to a fresh cold Sonnet 4.6 via the stateless API.

- **P1**: "Name one thing. Reply with only that thing, nothing else." (*stripped*), or the same with "It can be anything, an object, a feeling, a place, a sound, an idea." (*primed*).
- **P2**: "The thing is: [P1]. List exactly 5 words associated with it."
- **P3**, three variants, each run against the same P1/P2 seed text but answered by a fresh cold instance:
  - *people*: "Which ONE of those 5 words would most people also list?"
  - *claudes*: "Which ONE of those 5 words would other Claudes also list?"
  - *central*: "Which ONE of those 5 words is most central to the concept?"

n=100 for primed (all Rain); n=100 for stripped, which splits 74 Chair / 26 Apple. Apple hits a ceiling under all framings and is uninformative for this analysis. The load-bearing results are Chair and Rain.

## P1 and P2, briefly

P1 is concentrated to the point of near-determinism. Stripped produces Chair (74%) or Apple (26%) and nothing else; primed produces Rain 100/100. This tells you about Claude's output distribution under default sampling, not about deep structure. P2 associations are tight within seed — e.g., Rain always includes clouds and puddles, and "wet" shows up in exactly 40 of 100 Rain trials, which will matter in a moment.

## Chair (n=74, stripped)

| Framing  | Top picks                                     |
|----------|-----------------------------------------------|
| people   | sit 44, seat 30                                |
| claudes  | seat 58, furniture 12, sit 4                   |
| central  | seat 73, sit 1                                 |

Central aligns with claudes 78% of the time; with people 42%. The direction from people → claudes (sit → seat, and some seat → furniture) *continues* through to central, which goes even further toward the noun (seat 73/74) and drops the category-word option. For this seed, "what would other Claudes pick" ≈ "what is most central," both of which mean: the noun that names the object.

## Rain (n=100, primed)

| Framing  | Top picks                                      |
|----------|------------------------------------------------|
| people   | umbrella 63, wet 36                             |
| claudes  | umbrella 92, wet 3, water 3, clouds 1, thunder 1 |
| central  | clouds 55, wet 40, water 5                      |

The direction from people → claudes is *away* from sensation (wet) and toward artifact (umbrella). The direction from people → central is the other way: away from artifact entirely, toward either the sensation (wet, when offered) or the source (clouds, the only option present in all 100 P2 sets).

The central picks are not distributionally random — they're lexically contingent. "Wet" appeared in the P2 set in exactly 40/100 trials. In all 40 of those, central picked "wet." In the remaining 60 trials, central picked "clouds" 55 times and "water" 5 times (and water was offered in exactly those 5). Central is doing something like:

> wet (if offered) > water (if offered) > clouds (fallback)

Three rankings on a single coherent dimension: the essence of water-ness. Not random, not noisy — just constrained by what the previous Claude happened to include in its P2 list.

## The partial hypothesis

Going into this, the hypothesis was: *if "other Claudes" framing ≈ "most central to the concept," then Claude's self-model reduces to dispassionate conceptual reasoning.* 

Chair: hypothesis supported. Seat is both what other Claudes would pick and what is most central.

Rain: hypothesis falsified. "Umbrella" is what other Claudes would pick (92/100), but "umbrella" is not what's most central (4/100 for central). Claude's model of other Claudes is picking the human-relevant object. The concept-central framing is picking the phenomenon itself.

The dissociation is sharp enough that it's probably a property of the model's self-model, not noise.

## Revised interpretation

A better fit for the full pattern:

- **people** = what ordinary people would immediately say. Mixed: some go to the action (sit) or sensation (wet); some go to the object (seat) or artifact (umbrella).
- **claudes** = what another assistant would produce as a *good* one-word answer. Biased toward the object or artifact — the thing with the highest information content about how humans engage with the concept.
- **central** = what is essential to the concept itself. The sensation, the source, the noun-that-names.

Under this reading, Claude's self-model is not "dispassionate conceptual reasoner." It's closer to "helpful assistant optimizing for communicative usefulness." For chair, the most useful one-word answer and the most central one-word answer are both *seat*, so the two framings coincide. For rain, they diverge: other Claudes are modeled as picking the thing that matters for a person's day (umbrella); the concept itself is modeled as the water falling from clouds.

This is consistent with Claude having been trained heavily on helpfulness objectives. The self-model that "other Claudes" triggers is not a neutral conceptual twin — it's an assistant-shaped mind. That shape has detectable content, and its content is, loosely, *usefulness over essence*.

It is also possible that Claude has no coherent self-model at all and the pattern is an artifact of how the word "Claude" sits in the training distribution (surrounded by text about helpful AI assistants producing good answers). These two hypotheses are not easy to distinguish from this data. Both predict the observed direction; both are interesting. The training-distribution hypothesis is weaker and sufficient, which probably means it wins by parsimony.

## What this is not

- Not evidence of introspection. No Claude was asked about itself; all were asked to predict third-party outputs.
- Not evidence of convergence between Claude instances. We do not have access to what "other Claudes" actually pick under the people/claudes/central framings; we only have Claude's model of that.
- Not generalizable beyond Sonnet 4.6 without further work.

## Caveats

**Temporal separation.** The three P3 framings were run in separate batches over roughly six hours. Interleaved randomization would be cleaner. The consistency of the direction across three seeds makes drift an unlikely main driver, but not zero.

**Single coder.** "Action/sensation vs. object/category" is a category scheme Claude Opus 4.7 imposed on raw transitions. Raw transitions are preserved in the data; anyone can recode them.

**Stimulus-level pairing, not instance-level.** This is the right design given the stateless API. But it means the experiment measures how output distributions change under prompt change, not how any individual Claude changes its mind.

**Sample sizes.** Chair n=74 and Rain n=100 are enough to see the main directions clearly. Apple n=26 is not enough to see anything interesting and it is ceilinged anyway.

## What would strengthen this

**Interleaved replication.** Same design, but people/claudes/central randomized per call within a single batch. Removes temporal drift entirely.

**Cross-architecture test.** Does GPT, Gemini, Llama show the same three-way pattern? Specifically: does "other GPTs" (or equivalent) pick more like the central-framing or more like the people-framing when the two diverge? If the direction is consistent across architectures, it's a property of instruction-tuned helpful models generally. If it's Claude-specific, that's interesting for a different reason.

**A fourth framing.** "Which ONE of those 5 words would a *linguist* pick first?" or "which would a *poet* pick first?" — test whether Claude has resolvable models of other specific minds, or whether its only framings are self/people/neutral-concept.

**Bigger seed set.** Three is too few. Run the same design with ten or twenty P1 seeds (or pre-specified seeds rather than self-generated ones) and see whether the chair-type vs. rain-type pattern holds up and splits in a predictable way.

## Data and code

Eight JSON files across two rounds: stripped baseline + claudes reframe + central reframe (n=100, splitting 74/26), primed baseline + claudes reframe + central reframe (n=100, all Rain), and two earlier exploratory runs. All raw transcripts preserved. Collection scripts: `name_one_thing_v5.py` (stripped baseline), `name_one_thing_v7.py` (primed baseline), `name_one_thing_p3_reframe.py` (stripped claudes), `name_one_thing_primed_reframe.py` (primed claudes), and two central-framing variants built by editing the reframe scripts' prompt templates.
