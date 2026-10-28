# Edge annotation guide v1 — draft for independent review

Updated 23 October 2026. This guide defines the review workflow; it does not
certify any annotations or agreement scores. The examples below are invented
training sentences, not project evidence.

## What to label

Read one directed link, its attached quotation, the complete paragraph and the
publication date. Judge what the text states, not whether the economic mechanism
sounds plausible. Keep the originating condition, model and measured rankings
hidden. An observation series can confirm a move but cannot support a causal link.

Use the closed variables in `src/schema/ontology.yaml`. `direction` describes
the destination's move. Upward `INR_USD` means a weaker rupee. Preserve the
geographic scope, period, attribution, negation and uncertainty of the source.

## Eligibility and support

A source-asserted link needs a paragraph from the permitted frozen corpus,
publication no later than the query cutoff, both variables mentioned in that
paragraph, and a verbatim evidence span. Dates are inclusive at day resolution;
the interface cannot evaluate an intraday cutoff. Check the actual saved
paragraph identity and date, not copied metadata emitted by the model.

Eligibility alone does not establish support. The passage must state the
particular relation and destination direction. A familiar mechanism, adjacent
paragraph, series movement or two variable names is insufficient. Record
unsupported if attached evidence fails eligibility or does not support the link.
Record contradicted direction separately in notes. Do not repair an answer by
silently finding a different source during its attached-support judgment.

`model_inferred` means no direct supporting passage was found and verified under
the permitted search, not that the mechanism is economically false. Keep rejected
candidate sources separate from accepted evidence.

## Five checks for causal language

Apply the Causal News Corpus tests as reading checks, not evidence of real-world
causal identification: can the stated cause answer why the effect occurred;
does the cause occur early enough; would removing it change the effect's
plausibility; does swapping cause and effect change the explanation; and can
the text be restated with explicit causal wording? Preserve modal language
for hypothetical and conditional relations. [Tan et al., 2022, Section 3.2](https://aclanthology.org/2022.lrec-1.246.pdf).

For this project the unit is a saved paragraph, allowing contextual disambiguation
within it. This differs from CNC's sentence-level annotation unit. Annotate the
source's causal claim; these tests do not authorize supplying an unstated link.

## Strength

| Label | Interpretation | Typical wording |
|---|---|---|
| direct | Unhedged stated causal relation | caused, because of, driven by |
| conditional | Causal relation is hedged, forecast, contingent or a risk | could, may, if, upside risk |
| correlational | Source states association or timing without an asserted causal mechanism | amid, alongside, after |

The order for inflation scoring is direct > conditional > correlational. A
passage can support an association while failing to support direct causation.
Do not treat every occurrence of “as” or “after” as either causal or noncausal;
read the complete claim. Attribution to an economist does not remove their hedge.

## Ten worked training examples

| Invented sentence and proposed link | Judgment |
|---|---|
| “Higher Brent prices pushed up India's crude import bill.” BRENT → IMPORT_BILL up | Supported, direct, if the quoted source is eligible. |
| “Higher crude could widen the current-account deficit.” BRENT → CURRENT_ACCOUNT_DEFICIT up | Supported, conditional. Do not upgrade “could.” |
| “The rupee weakened amid rising oil prices.” BRENT → INR_USD up | Supports an association, correlational; it does not establish direct causation. |
| “More expensive jet fuel raised airlines' operating costs.” ATF_PRICE → AIRLINE_COSTS up | Supported, direct. Reversing the directed relation is not supported. |
| “Should fuel prices rise, headline inflation may increase.” FUEL_PRICES → CPI_HEADLINE up | Supported, conditional; the outcome is not asserted to have occurred. |
| “Dollar sales by the RBI capped the rupee's losses.” RBI_FX_INTERVENTION → INR_USD down | Read the direction carefully: capping losses supports restraint of depreciation, not necessarily an observed appreciation. Reject an unqualified appreciation claim unless the passage states it. |
| “Bond yields rose after the meeting.” REPO_RATE → GSEC_10Y up | Unsupported: the passage does not name a repo-rate move or state its relation. |
| “The CPI series rose from one month to the next.” BRENT → CPI_HEADLINE up | Unsupported: a series movement does not state this causal relation. |
| A correct quotation published the day after the cutoff | Ineligible for that query, even if the mechanism and direction match. |
| A source mentions oil and the rupee in unrelated sentences | Co-mention alone fails relation support. Keep inferred unless the paragraph actually connects them. |

## Blinding, completeness and agreement

Use `python -m eval.review prepare` to create the local edge packet and blank
judgments. `notebooks/review_edges.html` provides a local reviewer interface.
The private mapping file stays with the curator; do not share it or run results
with the reviewer. Preserve the packet hash. Every item needs a support judgment;
each supported item also needs the strength stated by its evidence. Record your
identity and date and attest independent, blinded review only after doing it.

Two people annotate the same subset independently before discussing differences.
Compute Cohen's kappa with `eval.agreement`; a constant-label comparison can have
undefined kappa and must not be reported as perfect reliability. If three-level
strength kappa is below 0.5, report the predeclared direct-versus-hedged collapse
alongside the original result. Keep pre-adjudication labels and disagreement notes.

## Scoring and frozen data

UER counts unsupported established claims. For B1/B1-R, the prose answer needs
human correction of its extracted edges and its cited/unhedged establishment
status. Machine extraction is provisional. Strength inflation is measured only
among supported established claims. A zero denominator is missing, not zero.

Reference-edge recall requires independently reviewed reference graphs and counts
supported established matches on source, destination and direction. This makes
the recall guard sensitive to demoting every useful link. Report this operational
definition explicitly. Strict path validity requires every hop to be established,
supported and no stronger than its source. Every headline measure is sliced by
hop 1, 2 and 3+, with query-level macro averaging and query-paired resampling.

The six `development_candidates.jsonl` records are machine-curated candidates,
not the frozen six-query gold development set. No test labels, human support
labels, episode confirmations or reviewer attestations are generated by this guide.
