# Independent review handoff

The original study calls for human correction of prose extractions and
condition-blind edge support judgments. The previously published descriptive
development scores and limited blind sample remain separate records.

## 1. Prose correction

Use one blank correction file per run. A corrector reads each prose answer,
compares it with the candidate graph, and fixes omitted, added or mislabelled
claims. Preserve the answer’s actual claims, citations and hedging, including
its mistakes. Keep uncited claims uncited and use only the passage attached
to a citation when correcting its quote. Established means cited or unhedged.
Update `established_edge_ids` when adding, removing or reclassifying a claim.
Keep nodes, hop distances and path labels consistent with any edge edits.
Keep source paths, source hashes, query identity, cutoff, anchor and condition
as supplied. Fill `correction_complete` for each finished case and sign the
identity, date and human correction fields after completion.

For a chosen run directory and matching corpus, from the repository root:

```sh
PYTHONPATH=src uv run python -m eval.prose_review prepare \
  --runs "$run_dir" --corpus "$corpus" --output "$blank_corrections"

# Run only after the human corrector returns the completed file.
PYTHONPATH=src uv run python -m eval.prose_review export \
  --runs "$run_dir" --corrections "$completed_corrections" --output "$corrected"
```

## 2. Blind support scoring

Use the corrected export to build the final packet, so reviewers do not score
edges that were subsequently added, removed or corrected.

```sh
PYTHONPATH=src uv run python -m eval.review prepare \
  --runs "$corrected" --corpus "$corpus" --output "$support"
```

Send only `packet.json`, the blank `judgments.json`, and
`notebooks/review_edges.html` to the support reviewer. Keep
`private_mapping.json`, condition names, model names, corrections and run
artifacts with the curator. The support reviewer must be independent and must
not have seen the condition mapping or comparison results for those items.
They use the HTML locally, score every edge against its attached passage, and
sign their own review date and attestations. For the agreement check, give a
second independent annotator the same shared subset before reconciliation.
Keep their original labels for the agreement calculation.

Place the returned `judgments.json` beside the original packet and private
mapping. The scorer checks the packet hash, item coverage, run-artifact hashes
and signed references. Use the dev reference directory for each development
arm, or the test reference directory for the two-query descriptive sweep.

```sh
PYTHONPATH=src uv run python -m eval.review score \
  --review "$support" --references "$references" --corpus "$corpus" \
  --output "$scores"
```

The two-query sweep falls below the ten-query inference threshold. Any
reviewed test result is descriptive. Treat bootstrap fields from the generic
scorer as internal diagnostics. Release aggregate results and receipts
without sharing licensed corpus text or the blind key.

## 3. Expand the test references

An expansion candidate requires a dated anchor, an as-of cutoff, and four to
six directed source-asserted edges with exact eligible spans. A co-mention
screen suggests passages to inspect. It cannot establish a causal link.
Screen for episode and citation overlap with development gold before any
candidate enters a frozen evaluation. Send each of two annotators a worksheet
that omits draft labels. They independently assess whether the passage asserts
the relation, and if so, its direction and strength. Record agreement, then
reconcile. Recheck exact spans, dates and hop structure on the reconciled
graphs. Use a fresh reference directory and run
`python -m eval.references --references "$references" --corpus "$corpus"`
with `PYTHONPATH=src` to create the blank hash-bound receipt. A reviewer signs
it only after checking the final graphs. Preflight the expanded query manifest
against that receipt before generating or inspecting new model outputs. Keep
the two currently signed references and their receipt unchanged while
expansion is in progress.
