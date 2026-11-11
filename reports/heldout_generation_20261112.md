# Primary held-out generation on two signed FPI queries

The pinned primary model generated **14 graphs across seven conditions** on
`test-fpi-why` and `test-fpi-effects` (20 April 2026 cutoff for both). The
queries share the March FPI outflow episode. Their signed references also
seed some items in the separate verifier challenge diagnostic. The
signed-reference preflight passed before generation. The run audit confirmed
the full matrix, graph and log checksums, run identities, successful stops
and tool-call counts. An unchanged resume reused all 14 saved results.

| Condition | Why edges | Effects edges | Why tool calls | Effects tool calls |
|---|---:|---:|---:|---:|
| B0 | 1 | 6 | 1 | 1 |
| B1 | 1 | 6 | 2 | 2 |
| B1-R | 1 | 6 | 2 | 2 |
| B2 | 6 | 6 | 2 | 2 |
| A-NoVerify | 6 | 6 | 9 | 3 |
| A-NoLoop | 6 | 6 | 12 | 12 |
| M | 6 | 6 | 12 | 12 |

All 14 runtime checks confirmed the signed queries' declared FPI threshold.
No post-cutoff passage appeared among 121 logged returned passage
occurrences. The structural source audit checks each asserted edge's corpus
membership, verbatim span and publication date. M and A-NoLoop passed these
checks. The audit found two nonverbatim spans, one in A-NoVerify and one in B2.

The bound logs record 34 model calls, 99,417 prompt tokens, 15,192 completion
tokens and 74 tool calls. Model calls occupied 2,224.6 seconds of summed wall
time. Summed per-graph wall time was 2,289.5 seconds (38.2 minutes), including
tools and excluding sweep startup.

## Reproduction and provenance

Run `make sweep-test-descriptive` from the project root with the local model
and frozen assets described in [reproduction](../docs/reproduction.md). Use
`TEST_OUTPUT` to select a fresh run directory and run `eval.run_audit` on it.

- Model `mlx-community/Qwen3-8B-4bit` at `545dc4251c05440727734bcd94334791f6ab0192`
- Query manifest SHA-256 `6160ccca0846eacc63a73aab5bcbca36da5e3cee9e67dfd2e1ff8446c1d26e6a`
- Signed test reference receipt SHA-256 `3d68111a038f549e7bc1c815da86708e5410c9f85d5874bcacb58de2e6415bd8`
- Corpus SHA-256 `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`
- Dense index SHA-256 `5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`
- Reranker revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`
- Run code SHA-256 `d0e083d15c2964cc09344a3896add2696ec61aa98af9696dec3fd94aee3841c8`
- Run inputs SHA-256 `0564443620e13dae2a97dc5e2ff63abfea0e95d529fefd08a075afd8d3341afa`
- Artifact receipts SHA-256 `189832f3af1c33ccd78a5b30194fd481158ead0d669f9c1ed864fed454c6ad2e`
- Local audit SHA-256 `7c38652b9745ced0134b820745bc187c074282b6de0d2550170314f6ef42cddb`

## Remaining review

Six held-out prose outputs and 24 development prose outputs have blank
human correction forms. Condition-blind support scoring follows correction.
This report records generation and structural checks. The two held-out
queries are below the ten-query inference threshold.

Fourteen unsigned expansion candidates across seven dated episodes were
checked against the visible series and screened for corpus evidence. The
period-limited screen excluded documents used in signed dev and test gold.
One four-edge candidate graph passed citation checks and has blank
worksheets for two reviewers. Expansion requires source-level adjudication
and a new signed receipt. The signed set currently contains two references.
See the [independent review handoff](../docs/independent_review.md).
