# Varun Patil: Track A status

Updated **22 October 2026** in the local project folder, branch
`varun` (continued from `a/corpus-retrieval-foundation`). **Varun's work is not all complete.** The
corpus/retrieval foundation is implemented and tested; research acceptance and
four macro series remain outstanding.

The project studies how textual support changes with hop distance through a
causal explanation graph. Every condition must share the corpus, date boundary,
model and first-stage retriever. Macro series only confirm measured moves;
they cannot support causal edges. The mid-submission is 30 October.

The project plan and ownership table assign Track A to Varun, Track B to Deepti,
and Track C to Harshal. GitHub's live issue list currently has **no individual
assignees**; all issues are open. This report follows the plan's ownership rather
than claiming that GitHub has assigned the issues to Varun's account. No issues
were closed, and no other owner's implementation was edited. This checkpoint
is intended for Varun's branch, with unfinished research work explicitly listed.

## Assignment status

“Software complete” means implemented and locally verified, not merged or
accepted on all team machines.

| Assignment | Status and evidence | Outstanding work |
|---|---|---|
| [A1 / #1](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/1) | Four publisher identities supported; paced, bounded collectors and resumable archive acquisition. ET and BusinessLine cover all seven months. | Business Standard access is blocked; Mint has only two March items. Source balance and broader extraction review remain incomplete. |
| [A2 / #2](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/2) | Real MoSPI, PPAC and OEA original releases, with date-source manifests and PDF extraction. A PIB mirror was acquired and exactly deduplicated against MoSPI. | RBI access/coverage is missing. OEA is an explicit source-list deviation. Unreadable or later-version files remain excluded. |
| [A3 / #3](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/3) | **Software complete:** normalized HTML/PDF documents, checksummed raw input, frozen Passage records and rejection audit. Current page recommendations and recognised promotions are filtered. | Broader manual extraction review; some opening sentences may be omitted and PDF tables can flatten. |
| [A4 / #4](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/4) | Deterministic exact/MinHash deduplication, duplicate audit, source-by-month manifest and reproducible zip. Distinct monthly official reports are preserved despite identical covers. | Final source/extraction/licence review. Count targets alone do not establish a final research freeze. |
| [A5 / #5](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/5) | **Software complete:** paragraph offsets address the exact archived parent text, including repeated paragraphs. | Preserve alignment through later corpus changes. |
| [A6 / #6](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/6) | **Software complete:** BM25 and merged aliases for all 46 ontology variables. | Research configuration selection awaits A8 review. Some inherited aliases are broad. |
| [A7 / #7](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/7) | Real pinned BGE-M3 on the local MPS GPU, FAISS and hybrid RRF; model/input-checked resumable embeddings and corpus-checked indexes. Initial 664-passage backend checks passed. | Full 27,286-passage encoding is in progress at this checkpoint. Keep reviewed corpus/model/input settings fixed for comparisons. |
| [A8 / #8](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/8) | Four-configuration runner, Recall@5/@10, MRR@50, hashes and simplest-within-0.03 rule; 20 source-backed development pairs prepared. | **Incomplete:** independent review and broader temporal coverage. Development results cannot freeze D-02. |
| [A9 / #9](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/9) | Real pinned cross-encoder and top-50 reranking implemented and exercised. | **Incomplete research evaluation:** uses the same unreviewed convenience pairs; D-03 remains open. |
| [A10 / #10](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/10) | Read/import layer plus **2/6 actual series**: 7 original provisional CPI observations and 141 daily FBIL USD/INR reference rates. Historical availability/vintages are enforced. | **Missing:** front-month Brent, Indian basket, benchmark 10-year GSEC yield and net equity-plus-debt FPI flows in USD million. |
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

The pairs are machine-curated, March-only, and have incomplete positive labels.
Keep all model/retriever choices hidden during independent review. Research
selection and shared decision-log edits remain pending. This is retrieval work,
not Deepti's event/edge annotations or anchor-episode confirmation.

At this commit, full-corpus model encoding and the corrected development pilot
are still running/pending locally. No corrected full-corpus metric table is
claimed here; it belongs in a follow-up checkpoint after validation completes.

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

The text corpus, zip, raw publisher files, model weights and embedding caches
remain local and ignored. Share the zip separately with its manifest checksum
only after reviewing source reproduction terms.

## Verification and later assignments

`make lint test` passed: **361 tests**, Ruff and Black. Tests cover source/version
exclusion, paragraph integrity, date boundaries, macro-series availability,
checkpoint interruption/model changes, candidate reuse and all retrieval modes.
The real backend checks and final snapshot audit are recorded alongside the
pilot and manifest.

Varun's later work is still pending: retrieval integration
[#33](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/33), the reviewed
retrieval table [#45](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/45),
figures [#46](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/46), and
fresh-clone/full-dev reproduction
[#50](https://github.com/DeeptiKoranga/lma-grounding-decay/issues/50).
The conditions runner, dev gold and generated run logs needed for those tasks
are not available on the current main-based checkout. They were not implemented
on behalf of Deepti or Harshal. Local unit checks do not replace the planned
all-laptop and seven-condition integration gates.
