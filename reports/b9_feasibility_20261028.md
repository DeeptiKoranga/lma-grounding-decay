# B9 challenge set cannot be built at 125 items — 28 October 2026

Issue #20 asks for 100 corrupted edges plus 25 clean controls, "semi-auto
generated from the dev gold edges". With the v7 corpus installed and the four
dev gold graphs drafted, that specification is **arithmetically unreachable**,
and no amount of further annotation inside the current design fixes it.

This is not a shortfall in effort. It is a consequence of D-18 and D-19 that
nobody costed at the time.

## The numbers

`src/eval/challenge.py` (Track A) gates generation on the reviewed gold set:

| gate | required | actual | shortfall |
|---|---:|---:|---:|
| eligible seeds — `source_asserted`, non-correlational, visible at as-of, span verbatim | 25 | **19** | 6 |
| hedged seeds, for the strength-inflation corruptions | 20 | **9** | 11 |

The dev gold set is 20 edges over four graphs: 10 `direct`, 9 `conditional`,
1 `correlational`; 15 at hop 1 and 5 at hop 2.

## Why more annotation will not close it

`eval.gold.MAX_EDGES` is 6 and D-19 left **four** dev queries, so the dev gold
set has a hard ceiling of **24 edges**. Even a maximal, fully adjudicated dev
set cannot reach 25 eligible seeds, because eligibility also drops every
`correlational` edge. The hedged gate is further out still: it would need 20 of
at most 24 edges to be hedged, which no honest reading of the corpus supports —
the sources assert plenty of these links flatly.

The chain is:

```
D-18  only 4 of 8 anchors survived        (3 confirmed + 1 redated)
D-19  so the query set is 8, not 30       (4 dev, 4 test)
B4    so the dev gold set is <= 24 edges  (4 graphs x 4-6)
B9    so 25 seeds is unreachable          (needs > 24 eligible)
```

Issue #20's "100 + 25" was written against the original 30-query design, where
the dev half alone would have carried roughly 150 gold edges.

## What to do instead

Three options, in the order I would take them.

1. **Rescope #20 to what the gold set supports, and say so.** 19 seeds × 5
   corruption types = 95 candidate corruptions, of which strength inflation can
   only supply 9. A defensible set is **19 clean controls plus corruptions at
   the per-type counts the gold set allows** (19 each for reversed relation,
   unsupported intermediate, wrong date and wrong target; 9 for inflated
   strength) — 85 items. Per-type detection rates are only interpretable
   alongside their denominators, so those counts must be printed next to every
   rate, not averaged away.
2. **Do not pad from the test gold graphs.** Seeding corruptions from test gold
   would leak the test set into a diagnostic the system is tuned against, which
   is the same mistake D-19 split the query set by anchor to avoid.
3. **Do not relax the gate in `eval/challenge.py`.** The 25/20 thresholds are
   Track A's, they are there on purpose, and lowering them silently would turn a
   documented limitation into an undocumented one. Changing them is a decision
   for whoever owns that file, recorded as a decision row.

## The gate that is actually blocking today

Separately from the arithmetic, `eval.references.validate` refuses any reference
graph set whose `review_receipt.json` lacks a complete attestation — reviewer,
date, `independent_review` and `all_relations_and_strengths_reviewed`. The
receipt is prepared and hash-bound to the v7 corpus
(`25ad7ad9…`) and to each of the four graph files, with those four fields left
**blank on purpose**: they are a human's to sign, and filling them in from here
would be fabricating a review receipt.

So #20, #42, #43 and #44 are all behind one human step, not behind the corpus.
See `data/eval/gold/dev/ADJUDICATION.md`.
