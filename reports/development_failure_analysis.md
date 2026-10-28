# Observed development failure cases — 23 October 2026

These are trace/structure findings, **not** a ranking of the worst semantically
unsupported edges. Independent human support judgments are absent, so the
planned “five worst dev cases” analysis cannot yet be ranked by research scores.
No output below has been silently corrected to improve a comparison.

| Case | Observation from the actual artifact/log | Consequence and required follow-up |
|---|---|---|
| B0, development candidate 06 | The prose discusses higher crude costs reducing oil-marketer profitability, but mechanical extraction produced zero edges. Candidates 02 and 04 also produced empty graphs despite explanatory background prose. | Empty denominators must stay null. Human correction must assess omitted links before UER; graph emptiness cannot be interpreted as successful grounding or complete abstention. |
| B1, candidate 04 | All six asserted edges fail exact quotation matching against their cited trusted passages. The prose also carries a broader explanation than one quoted fragment. | The structural check flags all six spans. A reviewer must separately judge attached support, direction and strength; a quote mismatch is not itself a complete semantic UER judgment. |
| B1-R, candidate 05 | The adapter rejected two duplicate candidate relations. Other reranked cases also include rejected duplicates. The raw candidates and errors remain logged. | Deduplication prevents counting the same relation twice. Human prose correction must check whether any distinct claim was lost; no gold recall can be inferred from edge counts. |
| B2, candidate 02 | Three self-labelled asserted edges contain nonverbatim evidence spans. | Self-labels do not establish support. Preserve these as baseline outcomes and send the actual cited text for independent review. |
| A-NoVerify, candidate 05 | Eight tool calls and repeated generator attempts ended at the two-searches-with-no-new-evidence stop condition; measured case wall time was about 399.5 seconds. | Repeated retrieval can consume time without new evidence. The ablation retains generator self-labels, so this stop is no certificate of support. Compare repair quality only after human review. |

Source artifacts remain under the ignored local run folders. Their final
per-file hashes and included phase membership are recorded in the assembled
run's `phases.json`. Structural flag counts, graph counts and actual model usage
are in `reports/integration_validation.json`; support scores remain pending.

The correction packet also exposes extractor-added document identifiers in
several uncited prose answers (B1 candidates 05/06 and B1-R candidates 01/06).
These identifiers must not be converted into valid citations to improve the
baseline. Faithful correction removes extractor-added citations when the actual
answer supplied none.

The separate frozen synthetic action probe later measured only 5/40 expected
tool choices (12.5%), despite 34/40 schema/cutoff-valid calls. This diagnoses
model/prompt selection work still needed; it is not an additional human-ranked
dev failure case or a score for the deterministic executed controller.
