# Varun Patil: Track A progress and handoff

Reviewed and implemented on **22 October 2026 (IST)**, on branch
`a/corpus-retrieval-foundation`. Base: `8f0e21c` (`origin/main`). Existing local
corpus/collector/BM25 work was retained and extended.

## Project understanding

The proposal measures whether textual support weakens with distance through a
causal explanation graph. All conditions must share the corpus, date boundary,
model and first-stage retriever. Macro series confirm anchor movements only;
they do not support causal edges. The mid-submission is 30 October. Varun owns
corpus acquisition, parsing, retrieval, macro series, retrieval results and
figures. Deepti owns extraction/verification/annotations; Harshal owns the model,
tools, controller, metrics and shared infrastructure.

Reviewed the eight-page proposal (including the graph and pipeline diagrams),
the work plan, contribution rules, decision log, frozen schema/ontology/tool
contracts, all existing Track A code/tests, GitHub issues and remote branches.
The other implementation packages on main are still scaffolds. The active
verifier implementation is on `origin/b/verifier-rules`, not yet on main.

## Task status

“Implemented” below describes software, not completion of the research dataset
or experiment. GitHub issues remain open until their acceptance criteria hold.

| Task / issue | Current result | Remaining acceptance work |
|---|---|---|
| [A1 / #1](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/1) | Bounded, paced, resumable collector for all four news identities; sitemap/RSS/Atom parsing; archive-month priority; robots and redirect checks; checksummed raw cache and rejection logs. Real ET and Mint ingestion verified. | Scale March–September acquisition across publications; review topical relevance and extraction quality. |
| [A2 / #2](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/2) | Curated official-release fetcher for RBI/MOSPI/PPAC/PIB; HTML/PDF extraction with sourced publication dates. One actual official CPI PDF downloaded and parsed. | Curate release manifests and acquire 60–90 documents across official sources. |
| [A3 / #3](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/3) | HTML/PDF → normalized parent documents and validated Passage JSONL, with raw checksum validation and rejection audit. | Review a representative extraction sample as acquisition expands. |
| [A4 / #4](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/4) | Deterministic MinHash/LSH candidates plus exact Jaccard, exact text deduplication, reproducible zip/hash, source-by-month manifest and licence notes. Initial snapshot explicitly provisional. | Reach coverage targets and review the final research freeze; current sample has zero duplicate removals. |
| [A5 / #5](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/5) | Exact paragraph character offsets into archived normalized parent text; repeated paragraphs handled correctly. | Continue offset and extraction checks on new sources. |
| [A6 / #6](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/6) | Portable BM25 retrieval and merged alias handover covering all 46 ontology variables. | Select the experimental configuration using A8. |
| [A7 / #7](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/7) | Lazy BGE-M3 adapter, exact dense scoring, optional FAISS, portable vectors checked against model/revision and corpus, hybrid RRF. Offline backend tests pass. | Install the selected optional packages, pin model revision, compute real corpus embeddings and run real FAISS/model checks. |
| [A8 / #8](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/8) | Four-configuration pilot runner; Recall@5/@10, MRR@50, shared corpus/pairs, hashes and the predeclared simplest-within-0.03 rule. | Independently review 20 query/evidence pairs, run the real models and report results. D-02 stays open. |
| [A9 / #9](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/9) | Lazy BGE cross-encoder adapter, top-50 eligible candidates, optional pilot comparison. Offline tests pass. | Run the actual reranker on the chosen first-stage retriever. D-03 stays open. |
| [A10 / #10](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/10) | CSV import/read layer for the six ontology series; units/provenance validation, publication dates and historical revisions; returns frozen GetSeriesResult. | Acquire and review the six actual series CSVs. No synthetic observations were inserted. |
| [A11 / #11](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/11) | Required as-of filtering before ranking/cutoff across BM25/dense/hybrid/reranking; future documents cannot affect BM25 scoring statistics. | Preserve these checks when Track C wires its tool adapter. |

## Current real corpus

`data/processed/MANIFEST.md` is the authoritative coverage/hash record:

- 35 documents: 32 Economic Times articles, 2 Mint articles, 1 PIB-hosted official CPI PDF.
- 664 passages, all published in March 2026; no other month is covered yet.
- 34 news versus the 900 minimum; 1 official versus the 60 minimum.
- Snapshot is **PROVISIONAL**, unsuitable for final retrieval comparisons.
- Every passage's offsets were checked against its exact archived parent text.
- Archive SHA-256: `48f50f879ec993bfd2e91adec677b21fc867064844e78f5002a0cb2f46787e89`.
- Reversing all input documents produced the identical archive hash.

Raw payloads, logs, JSONL text and the snapshot zip stay outside git. Only the
manifest, source metadata, code and tests are tracked.

The official seed is the [PIB release page](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238889&lang=2&reg=48),
published 12 March 2026 at 16:00 IST, and its linked
[CPI PDF](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/mar/doc2026312822001.pdf).
The release reports February observations; its document publication date is
March. Observation date and information availability must remain separate.

The earlier Business Standard probe stopped because robots.txt returned HTTP
403. The earlier BusinessLine sample was outside the corpus window. These
sources still need usable archive coverage. Explicit subscription metadata is
rejected. Current archive URL discovery can be large, so use bounded batches
and inspect acceptance/rejection logs rather than assuming discovery equals
corpus acquisition. The initial ET batch includes bank/regulatory headlines;
some may be peripheral to the anchor episodes and need topical review.

## Reproduce and continue

Run from the repository root. These commands set the source path explicitly.
The existing dev environment is installed; `make setup` is the shared setup for
a new checkout. PDF ingestion additionally needs the already declared optional
`pymupdf`; publisher extraction improves with `trafilatura`. Install only needed
optional packages, rather than every GPU/backend extra on a laptop.

```bash
make lint test

# Bounded date-targeted discovery and article collection.
PYTHONPATH=src uv run --no-sync python -m scripts.fetch.collect \
  --source economic_times \
  --feed https://economictimes.indiatimes.com/etstatic/sitemaps/et/news/2026-March-1.xml \
  --max-feeds 1 --max-articles 25 --max-requests 30 --macro-urls-only

# Reuse discovered URL JSONL with --url-file; counts describe this invocation.
PYTHONPATH=src uv run --no-sync python -m scripts.fetch.official \
  --manifest scripts/fetch/official_seeds.jsonl --max-documents 25

PYTHONPATH=src uv run --no-sync python -m corpus
PYTHONPATH=src uv run --no-sync python -m corpus.freeze \
  --documents data/interim/documents.jsonl --output data/processed
# Existing snapshots require explicit --overwrite after review.

PYTHONPATH=src uv run --no-sync python -m retrieval \
  'Brent rupee import inflation' --corpus data/processed/articles.jsonl \
  --as-of 2026-03-12 --k 5
```

Retrieval also accepts `--retriever bm25|bm25_alias|bge_m3|hybrid_rrf`,
`--dense-backend exact|faiss`, `--dense-index PATH`, `--rerank`, `--device`,
`--local-files-only`, and explicit embedding/reranker model/revision options.
Default BM25 never loads a dense model. A dense cache from another corpus or
embedding model/revision is rejected.

Official release-manifest rows require `source`, `url`, `title`, `published_at`
and `publication_date_source`. Review that publisher page's date before adding
the row. Never derive publication dates from PDF metadata, article URL dates,
sitemap lastmod or the collection time. Scanned PDFs require separate OCR
review; short/empty extraction is rejected.

The A8 pair-file format is one JSON object per line: `query_id`, `query`,
`as_of`, `relevant_passage_ids` (a nonempty list). Evidence IDs must exist in
the shared corpus and be visible at the query cutoff.

```bash
PYTHONPATH=src uv run --no-sync python -m retrieval.pilot_runner \
  --pairs PATH_TO_20_REVIEWED_PAIRS.jsonl \
  --corpus data/processed/articles.jsonl \
  --embedding-revision PINNED_MODEL_COMMIT \
  --dense-index data/processed/bge-vectors.json \
  --output reports/pilot_retriever.md
# Add --rerank --reranker-revision PINNED_RERANKER_COMMIT for A9.
```

The runner requires 20 pairs for a research pilot. `--smoke` permits smaller
functional checks and labels them explicitly; they do not resolve decisions.
No research pilot numbers have been produced yet. Metric selection does not
automatically close shared decision-log rows.

Series API and import/read commands are documented in `data/series/README.md`.
Track C can use `corpus.series.SeriesStore.get_series()` directly and adapt
retriever `Hit` records to `SearchCorpusResult`; its code was left untouched.

## Verification and next priorities

- `make lint test`: **316 tests passed**, Ruff and Black passed.
- An isolated archive of Deepti's verifier branch, with this alias table copied
  in, passed all **100** alias, normalization and rule tests. The shared
  checkout was not merged or modified to run that check.
- Real collection → PDF/HTML parsing → snapshot → date-filtered BM25 search
  was exercised. The real snapshot's 664 offsets and reordered-input checksum
  were checked.
- BGE weights, the real cross-encoder and the real FAISS backend have **not**
  been executed. Their offline tests use controlled backends.

Priority is to expand coverage to all seven months and official sources, review
extraction/topical quality, acquire actual macro series, then review 20 pilot
pairs and run A7–A9. Shared broad aliases inherited from the verifier handover
can match WTI/generic crude as BRENT, or a five-year bond yield as GSEC_10Y.
Coordinate precision tuning with Deepti before freezing the experiment; a
mention gate is not a causal-support judgement.

Later Varun work remains dependent on other tracks: pair integration
[#33](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/33),
retrieval results [#45](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/45),
figures [#46](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/46),
and the final fresh-clone/dev-run check
[#50](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/50).
The conditions runner and dev evidence annotations are not on main yet.
