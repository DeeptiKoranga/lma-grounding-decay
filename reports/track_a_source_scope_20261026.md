# Track A acquisition and source-use scope — 26 October 2026

This mid-submission checkpoint uses the sources actually acquired and records
the missing publishers as a deviation. It does not claim complete publisher
coverage or permission to distribute the text corpus.

## Acquisition disposition

Business Standard remains absent following the recorded robots-policy failure.
RBI remains absent: the public Bulletin entry point still returned a JavaScript
human-verification challenge on 26 October. No challenge was bypassed. Keep
these as documented acquisition shortfalls, rather than repeatedly retrying or
substituting another publisher's account as an official RBI document.
The [RBI entry point](https://bulletin.rbi.org.in/) and the previous bounded
checks are recorded in `track_a_source_gaps_20261025.json`.

The plan's acquisition fallback permits reporting a reduced source mix with
per-source counts. The present development delivery retains BusinessLine, ET,
Mint, MoSPI, PPAC and OEA, with its exact counts in the new manifest. OEA remains
an explicit source-list deviation. ET concentration and sparse Mint coverage
limit representativeness; meeting document-count targets does not remove that
limitation. No new data or historical availability is inferred from search
snippets.

## Source policy audit

The following primary policy pages were inspected on 26 October. These are
policy observations, not a legal determination or a publisher's permission.

| Publisher | Finding | Delivery treatment |
|---|---|---|
| Economic Times | Personal/noncommercial limits and restrictions on systematic storage, extraction and redistribution appear in its terms. | No redistribution clearance is claimed; full text, indexes and cached originals remain local. |
| BusinessLine / Hindu Group | Terms identify BusinessLine among covered services and restrict reproduction beyond permitted uses/licences. | No redistribution clearance is claimed; no full-text corpus is pushed to GitHub. |
| Mint | The current terms restrict systematic copying and sharing beyond permitted service features or a separate licence. | Full text remains local; no licence is inferred from public accessibility. |
| Business Standard | Content and database rights are retained by the publisher/licensors. | No corpus content was acquired; source remains excluded. |
| MoSPI | Its policy conditionally permits reuse of qualifying Category A datasets with attribution and applicable conditions; third-party material is excluded. | Do not assume every release or third-party component has been individually classified or cleared. |
| PPAC | Its policy requires permission for reproduction, accurate context and attribution; third-party material has separate rights. | No permission has been requested or granted; originals and extracted full text remain local. |
| OEA | A source-specific reproduction permission was not established in this check. | No blanket government-content licence is assumed. |

Policy sources: [ET](https://economictimes.indiatimes.com/terms-conditions),
[Hindu Group](https://www.thehindugroup.com/termsofuse.html),
[Mint](https://www.livemint.com/terms-of-use),
[Business Standard](https://www.business-standard.com/terms-conditions),
[MoSPI](https://www.mospi.gov.in/CopyrightPolicy),
[PPAC](https://ppac.gov.in/website-policies).

The repository delivery contains code, factual counts, hashes, source URLs,
judgment identifiers and reports. It does not grant rights to the separate
local archive or certify that all local research uses are permitted. No emails,
licence purchases, external sharing or publisher consents were fabricated.

## Evidence extraction scope

The new PDF text index deliberately contains coherent narrative rather than
isolated numeric cells. Detected tables, chart fragments, page furniture and
short contextless blocks remain in the original PDFs and local page/bounding-box
audit files. This avoids assigning guessed column labels or decimal positions.
It is not a full-text PDF transcription. Source spelling and joined-word defects
are preserved when present in the original, rather than silently rewritten.

Image-led news without a reviewed graphic transcription is excluded from the
text evidence corpus. Lifestyle/entertainment pages and embedded related-story
links are also excluded. The original v3 corpus and completed review remain
available as immutable historical inputs; changed passages need new index and
review identities.
