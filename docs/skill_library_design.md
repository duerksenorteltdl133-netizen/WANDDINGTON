# Evolving Skill Library — Design

> Upgrade the cross-experiment memory from static per-dataset summaries to a **persistent,
> evolving skill library**: distilled, trigger-conditioned, utility-weighted strategy fragments
> that transfer across phenotypes. Builds on the existing DeLM verified-admission machinery.
>
> Survey framing: Externalization (Zhou 2026) **Memory** pillar; PerTurboAgent 粗读.md #3.

## 0. Diagnosis — why current memory ≈ 0

The ablation shows removing memory *improves* LOO avg by +0.004. Current memory adds nothing because:

1. **Too coarse / dataset-specific.** An entry ("for IFNG, TCR + NF-κB families mattered, ML arm
   won") is an *episodic record of one experiment*, not a reusable rule. It doesn't fire on a new
   phenotype.
2. **Redundant with parametric knowledge.** Generic biology ("NF-κB is inflammatory") is already
   in the LLM weights — externalizing it is wasted tokens.
3. **Static, no feedback.** Built once in batch; never refined by whether it actually helped.
4. **Flat injection.** Top-4 by relevance, dumped as text every round, regardless of round state.

**Hypothesis for the skill library:** memory helps only if it encodes what the LLM does *not*
already know — **empirical, cross-experiment procedural patterns and calibrations** — and injects
them **conditionally** at the round where they apply.

## 1. Two stores: Memory (state) vs Skills (procedure)

Keep episodic memory (current `experience_memory.json`) mostly as-is — it is the raw material.
Add a second store, the **skill library** (`skill_library.json`), distilled *from* episodic
memory + full trajectories.

| | Episodic memory (have) | Skill library (new) |
|---|---|---|
| Unit | one experiment | one reusable rule |
| Content | what happened | when-then strategy fragment |
| Injection | top-4 flat | only *firing* skills, round-adaptive |
| Lifecycle | regenerated | acquired → verified → reinforced/retired |

## 2. Skill schema

```json
{
  "id": "sk_0007",
  "type": "pathway_prior | selection_heuristic | routing_meta | calibration",
  "trigger": {                      // when this skill fires (evaluated each round)
    "round": ">=2",
    "signal": "hit_enrichment(complex) > 2x_background",
    "dataset_stats": {"hit_rate": "<0.05", "n_genes": ">15000"}
  },
  "directive": "If revealed hits are enriched in a stable protein complex, spend the next batch on untested members of that complex before exploring new pathways.",
  "evidence": [                     // grounding — real experiments + observed effect
    {"experiment": "Replogle_K562_essential", "observed_delta_hit": 0.04, "genes": ["POLR2A","..."]}
  ],
  "utility": {"n_applied": 12, "n_helped": 9, "avg_delta_hit": 0.021, "confidence": 0.71},
  "status": "candidate | active | retired",
  "verified": true,                 // passed DeLM admission (§4)
  "provenance": {"distilled_from": ["...","..."], "created_round": "2026-07-09"}
}
```

Key: a skill is **structure over identity**. `pathway_prior` says "co-membership predicts
co-hit", *not* "gene X is a hit". This is what transfers and what dodges both parametric
redundancy and benchmark leakage.

## 3. Four skill classes (gene-selection-specific)

1. **`pathway_prior`** — empirical co-occurrence: hits enriched in complex/pathway P ⇒ prioritize
   untested members of P. Learned across experiments; triggered by *observed* enrichment, never by
   memorized gene names.
2. **`selection_heuristic`** — round-level policy: "after round r, if a family's hit-rate beats
   the pool baseline, allocate the next batch to its network neighbors"; "if ML and LLM disagree
   and LOO AUC is high, trust ML". These are the meta-decisions PerTurboAgent *hard-codes*
   (its "delayed start") — here they are learned and versioned.
3. **`routing_meta`** — learned replacement for the hand-tuned `waddington_c_arm._classify`
   thresholds: (n_genes, hit_rate, early-round signal) → fusion weights. (Adjacent to the
   "learned routing" direction; can be phased in later.)
4. **`calibration`** — "LLM confidence c ↦ empirical precision p(c)"; used to weight LLM votes in
   fusion. Purely meta, fully transferable, zero leakage.

## 4. Verified admission — extend DeLM to skills

Current `_verify_entry`: (phase 1) mechanical strategy-label check, (phase 2) LLM verifier for
gene-name hallucination. Extend to **three gates** for a candidate skill:

1. **Mechanical** — schema valid; trigger well-formed; every gene in `evidence` exists in the
   real pool (reuse current name check); `avg_delta_hit` recomputable from logged trajectories.
2. **Grounding (LLM-as-judge)** — does the evidence actually support the *general* rule, or is it
   overfit to one experiment? Reject over-generalization and spurious causal claims. (Reuses the
   phase-2 verifier prompt style.)
3. **Leakage guard (paper-critical)** — acquisition is strictly **LOO**: skills for fold *d* are
   distilled only from the other 8 datasets. Additionally, mechanically **reject any skill whose
   trigger/directive names a gene that is a hit in the held-out set**. This is the integrity check
   that lets us claim the lift isn't answer-memorization (cf. PerTurboAgent Table 7).

Fail-open only on transient LLM errors, as today.

## 5. Evolution — utility-weighted, no RL training

Credit assignment as a lightweight bandit, not gradient updates:

- Each round a skill is retrieved **and** applied, log whether that round's hit-rate beat the
  arm's running baseline → update `utility` (n_applied, n_helped, avg_delta_hit, confidence).
- **Promote** candidate → active once confidence and n_applied clear thresholds.
- **Retire** skills whose utility stays below a floor after *k* applications (decay).
- **Merge** near-duplicate skills (embedding similarity on trigger+directive) to prevent bloat.
- **Bounded capacity** (e.g. ≤ 40 active skills) → skills compete; this is what makes it *evolving*
  rather than monotonically growing (Evo-Memory style).

## 6. Retrieval — trigger-conditioned, round-adaptive

Replace flat top-4 with: at each round, evaluate every active skill's `trigger` against current
state (dataset stats + revealed hits + on-the-fly enrichment) → inject only **firing** skills,
ranked by `utility × relevance`, budgeted to top 3–5. Round 1 fires priors; later rounds fire
feedback heuristics. Rendered by a new `_build_skill_section` alongside the existing memory section.

## 7. Where it plugs into the code

| Component | Change |
|---|---|
| `waddington_select/skills.py` *(new)* | `SkillLibrary`: load / retrieve(state) / update_utility / persist to `workspace/results/sequential/skill_library.json` |
| `memory_builder.py` | add a **distiller pass**: LLM over full trajectory → candidate skills; reuse `_verify_entry`, extend with grounding + leakage gates (§4) |
| `arms/llm_reasoning_arm.py` | add `_build_skill_section`; after `update()`, emit the round outcome for utility logging |
| `arms/waddington_c_arm.py` | pass firing skills into the LLM arm; (phase 3) let `routing_meta` skills override `_classify` |
| `sequential_runner.py` | after each round, call `SkillLibrary.update_utility(skill_ids, delta_hit)` |

Trajectory logging: `sequential_runner` already tracks per-round hits/non-hits; add which skills
fired so credit assignment is exact.

## 8. Evaluation (paper-grade, honest)

- **Ablations:** full vs. `no_skills` vs. `skills_no_evolution` (static) vs. `skills_no_triggers`
  (flat inject). Isolates whether *evolution* and *conditioning* are what matter.
- **Target datasets:** does it lift the pathway-specific cases where both LLM and ML are weak
  (Steinhart, Carnevale22)? That is where transferable procedural knowledge should pay off.
- **Leakage audit:** shuffle held-out gene names — if skills encode *structure* not *identity*,
  the lift should largely survive; report the surviving fraction (this is our Table-7 analogue).
- **Pre-registered negative result:** if skills also add ≈0, that is a legitimate finding — in
  this LOO oracle the LLM's parametric knowledge subsumes externalized memory (survey's
  parametric-vs-externalized trade-off). We report it either way; no p-hacking the memory.

## 9. Phased rollout

- **Phase 1 (minimal, testable):** schema + `SkillLibrary` + trigger-conditioned retrieval + LOO
  acquisition + verified admission (reuse DeLM). *No evolution yet.* Measure vs. current memory.
- **Phase 2:** utility tracking + evolution (promote / retire / merge).
- **Phase 3:** `routing_meta` (learned `_classify`) + `calibration` skills into fusion.

Ship Phase 1 first — it is the smallest change that can already beat the flat top-4 memory, and it
de-risks the whole idea before investing in the evolution loop.
