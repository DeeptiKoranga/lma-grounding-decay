# One-query repeated-sampling stability check (#61)

Protocol was declared in `docs/stability_check_protocol.md` before the three
runs. Query `dev-oil-effects`, condition M, primary pinned Qwen3-8B, frozen v7
corpus and BGE-M3/FAISS index were held fixed. Decoding used temperature 0.7;
the only input difference **among the repeats** was the sampling seed. The
three `inputs.json` records differ only at `sampling_seed`. Each run passed a
complete, one-graph structural audit with zero failures.

| Seed | Proposed edges | Established edges | Established set | Model calls | Model-call seconds |
|---:|---:|---:|---|---:|---:|
| 1101 | 6 | 2 | A, B | 4 | 97.72 |
| 1102 | 6 | 2 | A, B | 4 | 89.94 |
| 1103 | 6 | 2 | A, B | 4 | 99.80 |

A is `BRENT -> INDIAN_BASKET` (up, correlational), citing
`economic_times-d356e5387611e02938c8#p2`. B is `BRENT -> INR_USD` (up,
conditional), citing `businessline-469aabd081e5b5594ab2#p9`. Both evidence
spans match byte-for-byte across the three repeats and the original greedy M
run. Generated edge IDs differ, so set equality uses variable pair, direction,
strength, hop, passage ID and evidence span.

The **proposed sets were not identical**. Four proposed links were shared by
all repeats: A, B, `INDIAN_BASKET -> ATF_PRICE`, and `ATF_PRICE ->
AIRLINE_COSTS`. The other two links in each run varied:

| Seed | Additional proposed links |
|---:|---|
| 1101 | `ATF_PRICE -> AIRLINE_SHARES`; `INR_USD -> IMPORT_BILL` |
| 1102 | `BRENT -> IMPORT_BILL`; `IMPORT_BILL -> TRADE_DEFICIT` |
| 1103 | `BRENT -> TRADE_DEFICIT`; `INR_USD -> FOREX_RESERVES` |

All moving links were unestablished. The established set is therefore stable
on this one query at these three seeds, while the proposal stage is visibly
stochastic. The two established edges exactly match the greedy run's judged
edge identities and evidence. Carrying forward that run's **assistant-produced**
support labels gives one supported edge out of two and UER **0.500 in each
repeat**. This is an identity-based reuse of existing labels, not a new blind
support review. It does not show that the three-query M-minus-B1 UER difference
is stable across queries, nor make the four-query development result inferential.

The three successful runs used 12 model calls, 19,809 prompt tokens, 2,982
completion tokens, **287.46 measured model-call wall seconds** and 36 tool
calls. This excludes model loading, retrieval and review. Their graph artifact
SHA-256 values, in seed order, are:

- 1101: `697a52b26accfe17b5d4837c643cd1af7d29add684ee70cfe3e7f9901a570647`
- 1102: `d1683f4d09ba6cc6a94800b0c3473e876bbd78f51a3d2a99ef62e2b475eecb32`
- 1103: `a192e5990bc3a15288266a8e232dc61727e26bb769d06ac7d18ea3887d77d6e0`

Raw graphs, logs and audits remain in ignored local `runs/stability-m-oil-effects-seed-*`
and `data/interim/stability-audit-*.json`; no corpus passage text is committed.
