# Pre-registration: the two-model sensitivity check on D-01

**Declared 9 November 2026, before any sweep has been run.** `runs/` is empty on
every machine as this is written. Everything below is a commitment made without
sight of a single result; the point of writing it down is that it cannot be
adjusted afterwards without the adjustment showing up in a diff.

Decided in #57 after the C2 pilot (#23, D-01) tied two models at 61.0% mean
accuracy and the pre-declared rule broke the tie on latency.

## What this is, and what it is not

It is **a sensitivity check on a confound**. It is **not** a model selection,
and it is not a second bite at D-01.

The confound is specific. `project_model_pilot_error_analysis_20261030.json`
shows the selected model, Qwen3-8B-4bit, names the wrong passage in 17 of 20
extractions and quotes nonverbatim in 10 of 20. Qwen3.5-9B-4bit does neither.
Those two fields — the passage cited and the span quoted — are exactly what two
of the four deterministic rules check (`in_corpus`, `span_verbatim`). An edge
that fails them never becomes eligible.

So a rise in UER with hop distance, which is what H1 predicts, has two possible
sources that the primary arm alone cannot separate:

1. **Grounding genuinely decays with distance.** The research question.
2. **The generator cannot cite accurately, and cites worse where the evidence is
   more tenuous**, which is deeper in the chain. UER would then rise with hop
   while measuring extraction failure.

One arm cannot tell these apart. Two can, because the second model has
essentially no citation-mechanics failure to contribute.

## The two arms

| | Primary arm | Sensitivity arm |
|---|---|---|
| Model | `mlx-community/Qwen3-8B-4bit` | `mlx-community/Qwen3.5-9B-4bit` |
| Revision | `545dc4251c05440727734bcd94334791f6ab0192` | `8b2b98c00a6b4d291155e4890773ca8f769aee53` |
| Config | `configs/model_selection.json` | `configs/model_selection_qwen35_9b.json` |
| Status | **Every headline number comes from here.** The pre-registered D-01 selection. | Reported beside it as a robustness check, never as the result. |

**The primary arm is primary whatever the numbers say.** If the sensitivity arm
produces a more flattering result, that does not promote it. Promoting the
better-looking arm after seeing both is the thing this document exists to
prevent.

Held identical across arms: corpus and its SHA-256, the four dev queries and
their as-of dates, the adjudicated gold set (D-26), retriever (BGE-M3) and its
index, the reranker, prompts, the rule layer, the seven conditions, the support
review protocol, and every gate in `src/eval/rq.py`. Only the generator weights
differ.

## What gets compared

Per arm, for each of the seven conditions, sliced by the hop buckets in
`eval.rq.BUCKETS` (1, 2, 3+):

- **UER** — the primary metric
- Strength inflation
- Reference-edge recall (the H2d guard)
- Provenance accuracy
- Strict path validity

Plus, as the diagnostic that makes this interpretable at all, the **rule-layer
rejection rate by rule and by hop**. If arm 1's edges are being lost to
`in_corpus` and `span_verbatim` while arm 2's are not, that is the confound
showing itself directly rather than being inferred from UER alone.

## The readings, declared in advance

The claim at issue is about **shape**, not level. H1 predicts UER *rises with
hop*. A model that cites badly should inflate UER at every hop; only a model
that cites badly *in a hop-dependent way* can manufacture the shape.

| Primary arm | Sensitivity arm | Declared reading |
|---|---|---|
| rises_with_hop | rises_with_hop | H1's signal is **robust** to generator citation quality. Report the primary arm; cite this as the check. The strongest outcome available. |
| rises_with_hop | no_monotone_trend or falls_with_hop | The rise is **plausibly an extraction artefact**. H1 is not supported by this evidence, and the report says the primary metric is confounded rather than reporting a decay result. |
| no_monotone_trend | rises_with_hop | The primary arm is **too noisy to detect** what the cleaner arm sees. Report no supported H1 finding from the pre-registered arm, and report the sensitivity arm as the reason to re-run D-01 properly for the final study rather than as a result. |
| no_monotone_trend | no_monotone_trend | **No decay detected** under either generator, which is a finding about this corpus and this scale, not about H1 in general. |
| insufficient_data (either arm) | — | The gates fired. Report the gate, not a trend. See below. |

A difference in **level** between arms, with the same shape, is expected and is
not evidence against H1: it is the extraction-quality gap doing what it should.

## What this cannot settle

`MIN_QUERIES_FOR_INFERENCE` is 10 and the dev set is 4 (D-19), **so that gate
fires by construction on every dev run, in both arms**. No interval here is
inferential and no result below it is a hypothesis test. `rises_with_hop` in
this document means the monotone-trend verdict from `eval.rq`, computed over
buckets that each clear `MIN_ESTABLISHED_PER_BUCKET`, and nothing stronger.

With 16 gold edges at 12 hop-1 and 4 hop-2 (D-26) and **nothing at hop 3**, the
`3+` bucket has no reference denominator in either arm, so `MIN_BUCKETS_FOR_TREND`
of 3 may well not be met. If it is not, the honest output is
`insufficient_data`, and this whole comparison reports a rejection-rate
diagnostic and no trend. That outcome is declared here as acceptable in advance,
so that it cannot later look like a failure worth working around.

Neither arm licenses a general claim about either model. This is 4 queries on
one corpus with one prompt set.

## Cost

Two sweeps instead of one. The sensitivity arm is roughly 30% slower per
generation (26.6 s against 20.4 s in the pilot), so budget about 2.3× the
single-arm wall-clock for the pair. Both arms must complete before either is
read, so that neither is interpreted alone.

## Why this rather than switching

Switching to Qwen3.5-9B would trade one problem for another, not remove it: the
pilot has it 20 points worse at strength labelling (75% against 95%) and 35
points worse at rejecting unsupported edges (60% against 95%). Those feed
strength inflation and the verifier's own job. Running both and declaring the
comparison in advance is the only option that neither hides the citation problem
nor quietly acquires a judgement problem in its place.
