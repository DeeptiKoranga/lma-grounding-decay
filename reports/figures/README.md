# Development example figure

`development_example_v7.svg` and its Graphviz source
`development_example_v7.dot` were rendered from the current-v7 local smoke
artifact `runs/connected_v7_smoke_20261027/M/dev-candidate-05.json` (SHA-256
`0910c29c847fc46a24cc63cd78ff56bb320fe26454a6ee70053f435f9f0dcb51`).
The cutoff is 31 August 2026. The figure shows model labels; independent edge
support review remains pending. The retained graph is in ignored local runs,
while the static figure and its source are committed for the mid-report draft.

`src/eval/figures.py` can render the UER-by-hop chart once completed reviewed
scores exist. No UER result chart is included here; the renderer rejects
unreviewed scores and labels missing hop denominators as N/A.
