# Development example figure

`development_example_v7.svg` and its Graphviz source
`development_example_v7.dot` were rendered from the current-v7 local smoke
artifact `runs/connected_v7_smoke_20261027/M/dev-candidate-05.json` (SHA-256
`0910c29c847fc46a24cc63cd78ff56bb320fe26454a6ee70053f435f9f0dcb51`).
The cutoff is 31 August 2026. This smoke figure predates the 10 November
support review and shows model labels. The retained graph is in ignored local runs,
while the static figure and its source are committed for the mid-report draft.

The assistant-labelled primary-arm UER-by-hop chart is `uer_by_hop.svg`, generated from
`reports/dev_gold_primary_reviewed.json` with `src/eval/figures.py`. It labels
missing hop denominators as N/A and displays the four-query development-only
scope. `gold_dev_oil_effects.*` and `gold_dev_rupee_why.*` are the static
adjudicated reference-graph examples used in the academic report.
