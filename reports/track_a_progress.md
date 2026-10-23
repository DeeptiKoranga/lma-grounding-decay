# Varun Patil: Track A status

Updated **23 October 2026** in the local project folder, branch
`varun` (continued from `a/corpus-retrieval-foundation`). **Varun's work is not all complete.** The
corpus/retrieval foundation and integrated development pipeline are implemented;
research acceptance, three missing series and partial basket coverage remain
outstanding.

The latest continuation is detailed in `reports/track_a_continuation.md`.
A separate **1,183-document, 26,888-passage corpus candidate** removes 564
explicit related-story paragraphs and adds ten eligible Mint articles, extending
that source to all seven months. Its 73-document extraction/source review is
prepared but blank. The active 1,173-document snapshot and prior experiment
hashes are preserved. Twenty new machine-curated retrieval questions now cover
March–September; their comparison remains unreviewed. Four FBIL yield candidates
are audited separately, with no canonical import. **Track A remains incomplete.**

The 23 October series continuation added two Indian basket monthly observations,
bringing canonical populated series to three of six, with partial basket coverage.
Five CDSL FPI monthly candidates remain outside the series store pending historical
vintage verification. See `reports/series_continuation.md` for the source audits,
reproduction commands in `data/series/README.md`, and the 412-test validation gate.

The project studies how textual support changes with hop distance through a
causal explanation graph. Every condition must share the corpus, date boundary,
model and first-stage retriever. Macro series only confirm measured moves;
they cannot support causal edges. The mid-submission is 30 October.

The project plan and ownership table assign Track A to Varun, Track B to Deepti,
and Track C to Harshal. GitHub's live issue list currently has **no individual
assignees** at the last inspection; all issues were open. This report follows the
plan's ownership rather than claiming GitHub assignments. The continued-project
integration adds Track B/C development components on this local branch and
credits the existing Track B rules in `reports/integration_status.md`. It does
not represent teammate review or merge acceptance. No issues were closed.

## Assignment status

“Software complete” means implemented and locally verified, not merged or
accepted on all team machines.

| Assignment | Status and evidence | Outstanding work |
|---|---|---|
| [A1 / #1](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/1) | Four publisher identities supported; paced, bounded collectors and resumable archive acquisition. ET and BusinessLine cover all seven months. Candidate revision adds ten eligible Mint articles and gives Mint all-seven-month coverage (12 items total). | Business Standard remains absent; Mint is still sparse. Candidate corpus acceptance, source balance and broader extraction review remain incomplete. |
| [A2 / #2](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/2) | Real MoSPI, PPAC and OEA original releases, with date-source manifests and PDF extraction. A PIB mirror was acquired and exactly deduplicated against MoSPI. | RBI access/coverage is missing. OEA is an explicit source-list deviation. Unreadable or later-version files remain excluded. |
| [A3 / #3](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/3) | **Software complete:** normalized HTML/PDF documents, checksummed raw input, frozen Passage records and rejection audit. The candidate revision additionally removes 564 explicit related-story paragraphs; regression checks cover their exclusion and revised offsets. | The 73-document review packet is blank. Unlabelled recommendations, omitted opening sentences and flattened PDF tables still need review. |
| [A4 / #4](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/4) | Deterministic exact/MinHash deduplication, duplicate audit, source-by-month manifest and reproducible zip. Distinct monthly official reports are preserved despite identical covers. | Final source/extraction/licence review. Count targets alone do not establish a final research freeze. |
| [A5 / #5](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/5) | **Software complete:** paragraph offsets address the exact archived parent text, including repeated paragraphs. | Preserve alignment through later corpus changes. |
| [A6 / #6](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/6) | **Software complete:** BM25 and merged aliases for all 46 ontology variables. | Research configuration selection awaits A8 review. Some inherited aliases are broad. |
| [A7 / #7](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/7) | Real pinned BGE-M3 on the local MPS GPU, FAISS and hybrid RRF; model/input-checked resumable embeddings and corpus-checked indexes. **Full 27,286-passage snapshot encoded; real saved-index reload passed.** Initial FAISS/exact backend agreement also passed. | Keep reviewed corpus/model/input settings fixed for comparisons. |
| [A8 / #8](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/8) | Four-configuration runner; March-only comparison preserved. Twenty new source-first machine-curated questions cover March–September, with 43 seed references and input hashes. The real broader development comparison is recorded separately. | **Incomplete:** independent relevance review and accepted corpus choice. Development results cannot freeze D-02. |
| [A9 / #9](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/9) | Real pinned cross-encoder completed top-50 reranking on the earlier March pairs and the new 20-query March–September set, including the separate corpus candidate. | **Incomplete research evaluation:** all comparisons still use unreviewed convenience seeds; D-03 remains open. |
| [A10 / #10](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/10) | Read/import layer plus **3/6 populated series**: 7 original provisional CPI observations, 141 daily FBIL USD/INR reference rates and 2 Indian basket monthly averages available from 17 June. Five CDSL FPI candidates and four newly extracted FBIL yield candidates have separate audits. | **Incomplete:** Indian basket coverage; front-month Brent; accepted benchmark 10-year GSEC yield and FPI data. FPI vintages and yield publication dates/benchmark roll are unverified. The conflicting July yield table is excluded. |
| [A11 / #11](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/11) | **Software complete:** as-of filtering before ranking/cutoff across BM25, dense, hybrid and reranking. Future documents cannot alter BM25 statistics. Known later-version source copies are excluded. | Track C integration must preserve the interface guarantees. |

## Data and review records

The current local snapshot has **1,173 documents: 1,112 news and 61 official**,
with **27,286 passages** across all seven months. Both numerical acquisition
targets are met. Economic Times contributes 892 news items, BusinessLine 218,
and Mint 2. Official coverage is MoSPI 37, PPAC 14, and OEA 10. One identical
PIB/MoSPI copy was removed. Forty-six known later-day versions were excluded.

All 27,286 offsets match their saved parent text. Every publication falls within
the frozen window, and every corrected pilot reference exists and is visible at
its cutoff. Reversing the original input order produced the identical archive
SHA-256, `ebef2e56b9db7c331289479e5dc9e67850edd5546364dc9844e79eeb6264a3f4`.
These checks establish integrity and reproducibility, not full manual acceptance.

- `data/processed/MANIFEST.md`: retained counts by source/month, duplicate policy,
  payload hashes, archive hash and source licence notes.
- `reports/corpus_validation.json`: full-snapshot integrity and temporal checks.
- `reports/acquisition_review.md`: source selection, temporal/extraction findings,
  blocked sources and remaining series gaps.
- `reports/pilot_pair_review.md` and `reports/pilot_pair_id_migration.json`: 20
  questions, 29 positive texts, source anchors and changes after source audits.
- `data/series/README.md`: actual acquired observations, exact units, provenance,
  and import/read commands.

The original 35-document snapshot is preserved locally under
`data/interim/initial_development/`. Its first pilot was invalidated by a later-day
article update and is explicitly superseded. Query 10 was corrected using an
eligible source before rerunning comparisons. The other positive texts were
preserved while IDs were adjusted after navigation removal and exact source
copy deduplication. No pair was adjusted to improve measured rankings.

The original pairs are machine-curated, March-only, and have incomplete positive labels.
They are preserved for provenance. The new temporal candidate pairs cover all
seven months; see the latest continuation for their separate corpus/input hashes.
Keep all model/retriever choices hidden during independent review. Research
selection and shared decision-log edits remain pending. This is retrieval work,
not Deepti's event/edge annotations or anchor-episode confirmation.

The corrected full-corpus comparison is complete in `reports/pilot_retriever.md`,
labelled **SMOKE CHECK ONLY; no research decision**. On the incomplete,
unreviewed labels, BM25 Recall@10 is 0.900; hybrid RRF is 0.925; BM25 plus
reranking is 0.975. BM25 is the simplest configuration within 0.03 of the best
first stage on these labels. This does not freeze D-02/D-03. The larger corpus
and corrected source audit make the superseded sample's scores incomparable.

All 27,286 passages were embedded with pinned BGE-M3; the saved full-corpus
artifact was reopened for a real FAISS search and its returned dates checked.
`reports/retrieval_run_provenance.json` records the model/runtime settings,
vector artifact checksum, cache reuse, the 977.67-second preliminary precompute,
and the 327.29-second corrected comparison. These are phase wall times, not
GPU-active time; the comparison time excludes earlier precomputation.

## Reproduce

Use the existing environment from the repository root. Optional packages installed
for the real run are recorded in the pilot report; the shared dependency files
were not edited. Python is 3.12.3. Model caches and vectors stay outside git.

```sh
UV_NO_SYNC=1 UV_CACHE_DIR=/private/tmp/lma-uv-cache make lint test

PYTHONPATH=src .venv/bin/python -m scripts.fetch.news_batch \
  --source economic_times --per-month 145 --workers 4 --max-requests 1500
PYTHONPATH=src .venv/bin/python -m scripts.fetch.news_batch \
  --source businessline --per-month 35 --workers 4 --max-requests 700
PYTHONPATH=src .venv/bin/python -m scripts.fetch.official \
  --manifest scripts/fetch/official_seeds.jsonl --max-documents 100 --max-requests 150
PYTHONPATH=src .venv/bin/python -m corpus --macro-only --output data/interim/research
PYTHONPATH=src .venv/bin/python -m corpus.freeze \
  --documents data/interim/research/documents.jsonl --output data/processed \
  --version v1 --overwrite
```

Review publication provenance before adding official seeds. PDF metadata may
flag a later file version but cannot date publication. Do not replace missing
series with a different financial definition or invent availability dates.
See the acquisition and series reports for raw-cache provenance.

The search CLI now defaults to the frozen `data/processed/articles.jsonl`.
For the development comparison on this machine, with the downloaded model cache:

```sh
HF_HOME="$PWD/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src \
  .venv/bin/python -m retrieval.pilot_runner \
  --pairs reports/retriever_pilot_pairs.jsonl --corpus data/processed/articles.jsonl \
  --smoke --device mps --max-length 1024 \
  --embedding-batch-size 8 --reranker-batch-size 1 \
  --embedding-checkpoint data/interim/retrieval/bge_m3_checkpoint.json \
  --checkpoint-every 400 --dense-index data/interim/retrieval/bge_m3_v1_vectors.json \
  --dense-backend faiss --embedding-revision 5617a9f61b028005a4858fdac845db406aefb181 \
  --rerank --reranker-revision 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e \
  --local-files-only --output reports/pilot_retriever_recheck.md
```

A new machine must download those pinned models first or omit offline/local-only
options to permit their normal public download. The 1024-token cap can truncate
long paragraphs; it is part of the recorded configuration.

The text corpus, zip, raw publisher files, model weights and embedding caches
remain local and ignored. Share the zip separately with its manifest checksum
only after reviewing source reproduction terms.

## Verification and later assignments

The current `make lint test` passes: **558 tests**, Ruff and Black. Tests cover source/version
exclusion, paragraph integrity, date boundaries, macro-series availability,
checkpoint interruption/model changes, candidate reuse and all retrieval modes.
The real backend checks and final snapshot audit are recorded alongside the
pilot and manifest.

Varun's later assignments include retrieval integration
[#33](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/33), the reviewed
retrieval table [#45](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/45),
figures [#46](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/46), and
fresh-clone/full-dev reproduction
[#50](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/50).
The conditions runner now connects the real corpus and model across all seven
conditions. Development logs and a structural audit are recorded separately in
`reports/integration_status.md`; independently reviewed development gold is
still absent. The retrieval table is an unreviewed smoke comparison, and the
qualitative graph carries pending-review labels. A fresh clone passes 545 core
tests with two optional-library skips. Its four-condition, one-query model probe
produces matching canonical graphs while reusing the heavy runtime and corpus.
These local checks do not replace
all-laptop, Kaggle, annotation or research acceptance gates.
