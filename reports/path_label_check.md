# Fixed-path label check

Three fixed synthetic reference paths from the Brent–Hormuz fixture were
checked by rebuilding paths from the fixture edges and joining by ordered edge IDs.
Both weakest-hop strength and all-hops-sourced status matched on **3/3 paths (1.000)**.
This tests deterministic aggregation from fixed edge labels. It does not test whether the
underlying edge judgments are correct.

| Edge sequence | Expected strength | Expected fully sourced | Match |
|---|---|---|---|
| e1 → e2 → e3 → e4 | conditional | no | yes |
| e5 → e6 → e7 | correlational | yes | yes |
| e8 → e9 | conditional | yes | yes |
