# Review handoff for the two completed dev sweeps

Both 28-graph sweeps passed structural audit; see
`reports/dev_gold_sweeps_20261110.md`. Their outputs remain in local ignored
`runs/` folders. Varun attests authorship and independent, condition-blinded
review of the 24 prose corrections and 247 edge judgments. The formal
correction exports and both `eval.review score` calls passed. See
[`dev_gold_varun_review_20261110.md`](dev_gold_varun_review_20261110.md)
for the reviewer record, scores, denominators and limits. This page retains
the workflow commands for reproduction.

## 1. Prose baseline correction (completed)

The completed local correction files are:

- `data/interim/assistant_dev_review_20261110/prose_corrections_qwen3-8b.json` — 12 B0/B1/B1-R
  answers from the primary arm.
- `data/interim/assistant_dev_review_20261110/prose_corrections_qwen35-9b.json` — 12 answers from
  the sensitivity arm.

For every item, compare `corrected_graph` against `prose_answer`. Correct
omitted, added or mislabeled edges without improving the answer's claims;
preserve its hedging and actual citations. Set `correction_complete` only after
checking that answer. Complete reviewer, date and human correction attestation
only when true. The sensitivity B0 outputs have prose but zero mechanically
extracted edges; zero edges must be checked for omissions, not accepted by
default. The primary B1 outputs also contain unresolved passage identifiers.

The completed exports used these commands:

```sh
PYTHONPATH=src .venv/bin/python -m eval.prose_review export \
  --runs runs/dev-gold-qwen3-8b \
  --corrections data/interim/assistant_dev_review_20261110/prose_corrections_qwen3-8b.json \
  --output data/interim/varun_corrected_qwen3-8b
PYTHONPATH=src .venv/bin/python -m eval.prose_review export \
  --runs runs/dev-gold-qwen35-9b \
  --corrections data/interim/assistant_dev_review_20261110/prose_corrections_qwen35-9b.json \
  --output data/interim/varun_corrected_qwen35-9b
```

## 2. Condition-blinded edge support review (completed)

Prepare from the *corrected* outputs, using distinct output directories. Give
the reviewer only each `packet.json` and `judgments.json`, under neutral packet
names; keep `private_mapping.json` out of view. The reviewer checks every
edge's cited passage, relation direction, as-of date and evidence strength.
Both arms were judged under the same rule. The reviewer attests that the
support judgments were independent and blinded to condition and results.

```sh
make review-dev DEV_OUTPUT=data/interim/varun_corrected_qwen3-8b \
  REVIEW_OUTPUT=data/interim/varun_support_review_packet_01
make review-dev DEV_OUTPUT=data/interim/varun_corrected_qwen35-9b \
  REVIEW_OUTPUT=data/interim/varun_support_review_packet_02
```

`eval.review` refuses incomplete judgments or missing independence/blinding
attestations. The packet hashes bind the exact graph artifacts. The reviewer
declarations record what actually happened; they are not inferred from the
presence of a file.

## 3. Score, report and draw the figure (completed)

Only after both packets and the signed dev reference receipt are in place:

```sh
PYTHONPATH=src .venv/bin/python -m eval.review score \
  --review data/interim/varun_support_review_packet_01 \
  --references data/eval/gold/dev \
  --output reports/dev_gold_primary_reviewed.json
PYTHONPATH=src .venv/bin/python -m eval.review score \
  --review data/interim/varun_support_review_packet_02 \
  --references data/eval/gold/dev \
  --output reports/dev_gold_sensitivity_reviewed.json
PYTHONPATH=src .venv/bin/python scripts/report_rq.py \
  --review-dir data/interim/varun_support_review_packet_01 \
  --rq1 reports/rq1_hop_decay.md --rq2 reports/rq2_verification.md
PYTHONPATH=src .venv/bin/python scripts/report_rq.py \
  --review-dir data/interim/varun_support_review_packet_02 \
  --rq1 reports/rq1_hop_decay_sensitivity.md \
  --rq2 reports/rq2_verification_sensitivity.md
MPLBACKEND=Agg PYTHONPATH=src .venv/bin/python -m eval.figures \
  --reviewed-scores reports/dev_gold_primary_reviewed.json \
  --output reports/figures/uer_by_hop.svg
```

The primary arm remains primary under D-28 regardless of the sensitivity
result. The RQ reports are development-only and must apply the predeclared
denominator, trend and recall gates. Rank the five worst cases for #47 only
after reviewed support scores exist; the older failure analysis is from v1.
