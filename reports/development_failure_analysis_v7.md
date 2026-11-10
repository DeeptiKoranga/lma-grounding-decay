# Five worst reviewed development cases — primary arm

Reviewed on 10 November 2026. This is a descriptive analysis of the four
development queries, not a test-set or population claim. The primary
Qwen3-8B arm is used for the planned five-case report; the Qwen3.5-9B arm is
the pre-registered sensitivity check.

Cases are condition–query graph artifacts, ranked by the **number of
unsupported established edges**. Ties use higher UER, lower reference-edge
recall, then condition and query ID in lexical order. This avoids treating an
empty graph as a zero-error success. The five selected cases each have six
unsupported established edges, UER 1.0 and reference-edge recall 0.0. Full
scores and artifact hashes are in `dev_gold_primary_reviewed.json` and
`dev_gold_qwen3-8b_audit.json`.

| Rank | Case | Category | What the reviewed artifact shows | Source artifact SHA-256 prefix |
|---:|---|---|---|---|
| 1 | A-NoVerify · dev-rupee-effects | Wrong passage reused across claims | All six established edges cite one paragraph about rupee levels and intervention. It does not state the asserted import-cost, trade-deficit or price-index relations. Structural source checks pass, showing that a valid citation is not necessarily semantic support. | `ead62c5baeed` |
| 2 | A-NoVerify · dev-rupee-why | Unsupported chain and reversed direction | Six established edges are unsupported. One quote is nonverbatim; the cited oil-war passage runs from oil risk to rupee pressure, while the generated edge reverses it. Other cited paragraphs do not state the proposed inflation/CPI chain. | `d93afaf911b9` |
| 3 | B2 · dev-oil-why | No attached evidence | The six established edges form an oil-to-import-bill-to-rupee story, but none has a cited saved passage. Structural source checks pass because this baseline makes no verified-source claim; semantic support remains absent. | `c4099868374d` |
| 4 | B2 · dev-rupee-effects | Wrong passage reused across claims | The same rupee-level paragraph is attached to six separate import, trade and inflation effects. None of those relations appears in that paragraph. This repeats the first case under the B2 condition. | `e2c20cae1d9f` |
| 5 | B2 · dev-rupee-why | Unsupported chain and reversed direction | The six-edge chain repeats the second case under B2. One quote is nonverbatim; the rupee-to-Brent edge reverses the direction of the cited passage, and other links lack their claimed causal support. | `0d196d929c74` |

The two repeated patterns are not five independent failure mechanisms. They
show that changing the condition did not remove the same source-selection and
direction errors for these queries. The top cases also show why the semantic
review was needed: an artifact can pass mechanical citation/date/span checks
yet still attach an unrelated passage to an established edge. None of these
cases is silently corrected in the original run output.
