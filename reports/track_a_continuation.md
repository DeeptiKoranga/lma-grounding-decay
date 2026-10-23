# Track A continuation — 23 October 2026

Track A has more completed local preparation, but is **not research-complete**.
Independent relevance review, corpus/source acceptance, macro-data gaps and the
reviewed full-development reproduction remain open. No human judgments or
research decisions were generated.

## Corpus revision prepared

`scripts/prepare_corpus_revision.py` stages a separate candidate under
`data/interim/corpus_revision_20261023/`. It preserves the active `data/processed/`
snapshot and every existing experiment, index and review packet.

- Ten new eligible Mint articles cover April–September. Together with the two
  existing March articles, the candidate has Mint coverage in all seven months.
  The sample is still small and concentrated on inflation/monetary policy.
- Eleven public pages were checked through the paced, robots-aware collector;
  one explicitly paywalled page was rejected. Each admitted page has matching
  publication/modification days and a checksummed raw payload.
- **564 explicitly labelled related-story paragraphs in 305 existing ET
  documents** were removed in the candidate. The ingestion parser now rejects
  standalone “Also read:” / “Also read |” / “Read more:” labels. Ordinary body
  sentences containing those words are preserved. Unlabelled recommendations
  remain a limitation.
- The candidate has **1,183 documents: 1,122 news and 61 official**, and **26,888
  passages**. All passage offsets match the exact revised parent text. Reversing
  the input order produces the same archive hash.
- A deterministic source/month sample of **73 documents** has a local extraction
  review packet. All extraction, publication/version and source-terms judgments
  are blank. Preparing this sample does not count as human review.

See `reports/corpus_revision_audit.json` and
`reports/corpus_revision_manifest.md`. The local sample is
`data/interim/corpus_revision_20261023/extraction_review.md`, with editable
`extraction_judgments.json` beside it. Review the full raw page/PDF, not just the
first and last paragraphs in the packet.

RBI and Business Standard are still absent. A newly discovered official RBI
mobile page was checked through its own robots policy; the robots request
returned HTTP 418 and collection stopped. See `reports/rbi_mobile_acquisition.json`.
The prior Business Standard access failure remains unresolved. No restriction
or paywall was bypassed, and no source redistribution permission is claimed.

## Broader retrieval pilot

Twenty source-first machine-curated questions now span March–September:
three per month through August, and two in September. Their 43 seed passages
cover currency, freight, monetary policy, capital flows, manufacturing costs,
aviation, food prices, exporter revenues and energy margins. Three questions
seek official CPI levels; those are retrieval questions, not causal evidence.
Queries and seeds were fixed before running this new comparison.

`reports/retriever_temporal_provenance.json` records input hashes, source
identities and limitations. `reports/retriever_temporal_id_migration.json`
maps all 43 seed texts exactly to the candidate corpus: 12 paragraph IDs change,
while query wording, cutoffs, source identities and evidence texts stay fixed.
No query was adjusted to improve a ranking.

The broader run on the active corpus is recorded in
`reports/pilot_retriever_temporal_development.md`. Its unreviewed Recall@10
is 0.4333 for plain BM25 and 0.6500 for hybrid RRF, versus the earlier March-only
smoke comparison's 0.9000 and 0.9250. These are different question sets with
incomplete seed labels; the numbers are not a controlled measure of deterioration.
The change in development preference demonstrates why the March convenience
sample could not settle D-02. **D-02 and D-03 remain open.**

The candidate corpus comparison, index and blinded packet are prepared separately
and must remain bound to that candidate's hashes. A corpus acceptance/change
requires matching pairs, indexes, review packets and experimental reruns; it
cannot reuse a v1 receipt by renaming files.

The candidate run completed in **183.14 seconds** on CPU, including newly needed
embeddings, four first-stage configurations and top-50 reranking. On its
unreviewed seeds, Recall@10 is 0.4333 (BM25), 0.5167 (aliases), 0.6000 (dense)
and 0.6250 (hybrid). The predeclared 0.03 tolerance picks dense for this smoke
run; dense plus reranking reaches 0.7667. These are development diagnostics,
not an accepted configuration or independently established recall.
See `reports/pilot_retriever_temporal_candidate_development.md` and
`reports/retrieval_temporal_run_provenance.json`.
The saved 26,888-passage candidate index was reopened in a separate process;
real pinned-model searches at March and September cutoffs passed in 15.55
seconds. See `reports/retrieval_temporal_saved_index_validation.json`.

The local blinded packet `data/interim/retrieval_review_temporal_v3/` has
**2,057 query–passage items for 20 questions**, with all judgments and reviewer
attestations blank. Candidates from all four top-50 pools and all 43 seeds are
retained, deduplicated and cutoff-checked. Ranks, scores and seed membership are
hidden. A real export attempt with blank judgments was rejected without writing
an accepted output. `reports/retrieval_temporal_review_readiness.json` records
the hashes and integrity checks. Resolve corpus acceptance before assigning
this packet, and keep the pilot reports hidden from its reviewer.

## Macro source audit

The canonical series store still has **three of six series populated**, with
only partial Indian-basket coverage. This continuation does not promote any
unverified historical vintage.

FBIL's public publication listing identified original newsletter assets, rather
than relying on a search engine's alternate PDF copy. Five PDFs were downloaded
and checksummed. The sovereign-yield tables on issue 86 page 3 and issues 87–90
page 4 were rendered and visually inspected by the agent.
`scripts.fetch.fbil_newsletters` reproduces the offline audit:

| Observation month | Printed month-end yield (%) | Coupon / maturity | Result |
|---|---:|---|---|
| March | 7.03 | 6.48%, 6 October 2035 | Candidate only |
| April | 7.01 | 6.48%, 6 October 2035 | Candidate only |
| May | 7.04 | 6.48%, 6 October 2035 | Candidate only |
| June | 6.75 | 6.94%, 11 May 2036 | Candidate only |
| July | — | Header says July; footnote says June | Excluded |

The first four are outside SeriesStore: media upload timestamps do not establish
newsletter publication dates, and the historical benchmark roll still needs
verification. They have `available_on: null`. Average YTM and par yields were
not substituted. The September-labelled asset was uploaded in October, so it
cannot fill an in-window publication gap without an earlier original.
See `reports/gsec_acquisition_review.json` and the primary
[FBIL publication listing](https://www.fbil.org.in/publications).

Brent still needs a source matching front-month futures and a documented roll;
spot Brent does not satisfy the ontology. Indian basket needs additional
original dated observations. The five previously staged CDSL FPI candidates
still lack historical revision/vintage proof. The accepted CPI/FX/basket files
and their availability dates are unchanged.

## Verification and remaining acceptance

The first broader retrieval attempt exited with code 139. A CPU retry stalled
at a FAISS OpenMP join; its process sample is retained locally at
`/private/tmp/lma-retrieval-stall-20261023.txt`. The completed retry explicitly
uses one FAISS thread per singleton search. This follows the caller-controlled
thread interface in [FAISS's documentation](https://github.com/facebookresearch/faiss/wiki/Threads-and-asynchronous-calls).
The original crash's exact cause is not established by the later stall sample.
The subsequent comparison completed; failed attempts produced no accepted scores.

Local Ruff/Black checks and **558 tests pass**. Tests exercise related-link
exclusion/offsets, candidate isolation and overwrite refusal, corrupted raw
input rejection, yield-column identity and conflicting month-label rejection.
The real full-corpus comparison also exercises the thread handling change.

Remaining work is concrete:

1. A human reviews the extraction/source-terms sample and resolves remaining
   source-balance/omission concerns before accepting a corpus revision.
2. An independent blinded reviewer completes retrieval relevance judgments;
   the reviewed comparison then informs D-02/D-03 acceptance.
3. Obtain acceptable original data/vintages for Brent, benchmark yields, FPI and
   the missing Indian basket months, or explicitly approve/report a reduced scope.
4. Once cross-track development gold and prose/support judgments exist, produce
   the reviewed retrieval table, UER figure and full reviewed fresh-development
   reproduction. Other team-machine checks remain pending.

The earlier local qualitative figure and four-condition fresh-source probe are
still development evidence. None of the preparation above makes the full
mid-submission or all-track acceptance complete.
