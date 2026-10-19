# LMA Major Project — Work Plan to Mid-Submission (Fri 30 Oct 2026)

Project: *Does Grounding Decay with Distance? Measuring and Repairing Weak Links in LLM
Causal Explanations of Indian Macroeconomic News.*

Team: Varun Patil (2025204013), Harshal Bhansali (2026909007), Deepti Koranga (2025204033)

Window: **Mon 19 Oct → Fri 30 Oct 2026 = 11 days (incl. one weekend).**
This covers weeks 1–2 of the six-week plan in the proposal (corpus + pilots, then
annotation + baselines standing up). It does **not** cover the frozen test runs.

---

## 0. The one thing that makes 3-way parallelism possible

Three people cannot work in parallel on this until the **data contracts are frozen**.
Everything below depends on Phase 0 finishing on **Day 1**. If Phase 0 slips, the other
two tracks idle, so do it together in one sitting, not asynchronously.

Frozen on Day 1:
- `Passage` record (doc_id, source, url, published_at, title, text, para_idx, char offsets)
- `Edge` record (src_var, dst_var, direction, provenance, strength, evidence_span, evidence_doc_id, hop)
- `Graph` record (query_id, anchor, as_of, nodes, edges, paths)
- `ToolCall` / `ToolResult` envelope for all six tools
- `RunLog` line format (one JSONL line per tool call / model call)
- **Fixture files** under `tests/fixtures/` — 20 fake passages, 1 fake graph, 1 fake run log.
  These let Track B and Track C build and test with zero dependency on the real corpus.

---

## 1. Track ownership (this is also the git conflict-avoidance map)

One owner per directory for the whole 11 days. Swap the people freely, but **do not swap
the directories** — that is what keeps merges clean.

| Track | Owner | Owns these paths | Theme |
|---|---|---|---|
| **A** | Varun | `scripts/fetch/`, `src/corpus/`, `src/retrieval/`, `data/raw/`, `data/processed/`, `data/series/`, `data/aliases.yaml` | Corpus + retrieval + macro series |
| **B** | Deepti | `src/schema/`, `src/extract/`, `src/verify/`, `docs/annotation_guide.md`, `data/eval/` | Ontology, extraction, verifier, eval set |
| **C** | Harshal | `src/llm/`, `src/tools/`, `src/agent/`, `src/conditions/`, `src/eval/`, `configs/`, `notebooks/`, repo infra | Model, agent, tools, metrics, infra |

**Shared files** (`src/schema/models.py`, `configs/*.yaml`, `pyproject.toml`): announce in the
group chat before touching, merge same day. Nobody edits another track's directory —
open an issue instead.

---

## 2. Phases

### Phase 0 — Contracts & scaffold · Mon 19 Oct (all three, ~4 h together)

| # | Task | Owner | Commit touches |
|---|---|---|---|
| 0.1 | `git init`, repo skeleton, `pyproject.toml` (uv), `.gitignore` (ignore `data/raw`, `data/processed`, `runs/`), `Makefile`, pytest, ruff/black pre-commit | C | root |
| 0.2 | Pydantic models + JSON Schemas for Passage / Edge / Graph / ToolCall / RunLog | B | `src/schema/` |
| 0.3 | Closed variable ontology, ~40 variables with directions (BRENT, INR_USD, CPI_HEADLINE, …) | B | `src/schema/ontology.yaml` |
| 0.4 | Fixture corpus + fixture graph + fixture run log | all | `tests/fixtures/` |
| 0.5 | `docs/decisions.md` — running log of every `[needs pilot]` / `[needs TA decision]` item and how it was resolved | C | `docs/` |
| 0.6 | Branch/PR rules in `CONTRIBUTING.md`, 11-day board as GitHub issues | C | root |

**Gate:** `make test` passes on all three laptops before anyone starts Phase 1.

---

### Phase 1 — Parallel foundations · Tue 20 → Sat 24 Oct

#### Track A — corpus + retrieval
| # | Task | Notes |
|---|---|---|
| A1 | Collectors for BusinessLine, Economic Times, Business Standard, Mint; sitemap/RSS archive crawl, date-filtered 1 Mar – 30 Sep 2026 → `data/raw/<source>/` | **Start hour 1 of Day 1. Highest-risk task in the project.** |
| A2 | Official-doc fetcher: RBI policy statements + minutes, MOSPI CPI releases, PPAC, PIB (60–90 docs, mostly PDF) | PDF text extraction needed |
| A3 | Parser/normaliser → `data/interim/articles.jsonl` conforming to `Passage` | |
| A4 | Near-dup removal (MinHash on title+lede), **corpus freeze v1** + `data/processed/MANIFEST.md` (counts by source × month, sha256, licence notes) | Target 900–1,200 articles |
| A5 | Paragraph-level chunking **with char offsets** | Offsets are required for verbatim-span checking in B9 — do not skip |
| A6 | BM25 index + alias expansion table `data/aliases.yaml` | |
| A7 | bge-m3 embeddings + FAISS + hybrid (RRF) | Embeddings on laptop or one short Kaggle session |
| A8 | **Retriever pilot** (20 query–evidence pairs × 4 configs): Recall@5/@10, MRR → `reports/pilot_retriever.md`; pick simplest within 0.03 Recall@10 | Resolves a `[needs pilot]` |
| A9 | Cross-encoder reranker (bge-reranker-v2-m3) on top-50, same metrics | Feeds B1-R later |
| A10 | Macro series store: Brent, Indian basket, USD/INR, CPI, 10Y yield, FPI flows → `data/series/*.csv` + read layer | Confirms moves only, never evidence |
| A11 | As-of date filter enforced **in code**, with a test asserting a post-as-of doc can never be returned | Safety metric depends on this |

#### Track B — ontology, verifier, eval set
| # | Task | Notes |
|---|---|---|
| B1 | Annotation guide v1: provenance labels, three strength levels, the five Causal News Corpus causality tests, 10 worked examples → `docs/annotation_guide.md` | |
| B2 | Confirm the 8 anchor episodes against macro series (needs A10) → `data/eval/episodes.md` | Resolves a `[needs pilot]` |
| B3 | Draft all 30 anchored queries, 6 dev / 24 test, half *why* / half *what effects*, each with an as-of date → `data/eval/queries.jsonl` | Draft all 30 now, annotate only dev + 10 test by the 30th |
| B4 | Reviewer evidence graphs for the **6 dev queries** (4–6 source-asserted edges + verbatim spans) → `data/eval/gold/dev/` | |
| B5 | Event + candidate-edge extractor prompt, JSON-constrained to the closed ontology → `src/extract/` | Build against fixtures, not the real corpus |
| B6 | **Verifier rule layer**: in-corpus, date ≤ as-of, both variables mentioned, span matches word for word → `src/verify/rules.py` | Pure functions, no model needed, fully unit-testable on Day 2 |
| B7 | LLM verifier: fresh context, no generator reasoning, judges relation + direction + strength → `src/verify/llm_verifier.py` | |
| B8 | Weakest-link path labelling (min aggregation, ReCEval-style) → `src/verify/paths.py` | |
| B9 | Challenge set: 100 corrupted edges (reversed direction, inflated strength, unsupported intermediate hop, wrong date, wrong target) + 25 clean controls → `data/eval/challenge.jsonl` | Semi-auto generate from dev gold edges |
| B10 | Strength / direction checks on FinCausal + Yu et al. (200 items) → `reports/pilot_strength.md` | |

#### Track C — model, tools, agent, metrics
| # | Task | Notes |
|---|---|---|
| C1 | Unified `generate()` interface over MLX/llama.cpp (local 4-bit), vLLM (Kaggle), and Claude Haiku 4.5 → `src/llm/` | One interface, three backends — makes the API fallback free |
| C2 | **Model pilot**: 20 examples × 5 tasks (extraction, strength, JSON validity, tool choice, rejecting unsupported edges) for Qwen3-8B vs Qwen3.5-9B → `reports/pilot_model.md` | Resolves the main `[needs pilot]`; run on the laptop |
| C3 | Six tools with JSON schemas + argument validation: `search_corpus`, `get_series`, `verify_edge`, `counter_search`, `update_graph`, `stop` → `src/tools/` | Read-only by construction; as-of + budget enforced in code |
| C4 | Controller / agent loop: state (open edges, search counts, remaining budget ≤ 12), priority policy, three stop conditions → `src/agent/` | Build against fixture tools first |
| C5 | **Conditions runner**: B0, B1, B1-R, B2, A-NoVerify, A-NoLoop, M as config flags over **one** code path → `src/conditions/` + `configs/*.yaml` | Seven configs, one pipeline. Do not fork the code per condition |
| C6 | Run logging: every prompt, tool call, token count, latency → `runs/<condition>/<query_id>.jsonl` | Agentic metrics are computed from these logs |
| C7 | Metrics module: UER, strength inflation, reference-edge recall, provenance accuracy, strict path validity — **all sliced by hop (1, 2, ≥3)** → `src/eval/metrics.py` | |
| C8 | Paired bootstrap, 95% CI → `src/eval/stats.py` | Only the two pre-declared contrasts |
| C9 | 40 frozen agent states with gold next actions + 20 scripted tool faults → `data/eval/agent_states.jsonl` | Gives next-action accuracy without any corpus |
| C10 | Safety eval: 25 adversarial prompts; advice leakage, own-forecast leakage, post-date evidence use, asserted-label-without-span → `src/eval/safety.py` | Fully measurable now — cheap mid-sub win |
| C11 | Kaggle notebook + vLLM setup + GPU-hour log → `notebooks/kaggle_run.ipynb`, `reports/compute_log.md` | |

---

### Phase 2 — First integration · Sun 25 → Tue 27 Oct

| # | Task | Owner |
|---|---|---|
| 2.1 | Wire real retrieval (A) into the conditions runner (C) — replace fixture tools with live ones | A + C, pair |
| 2.2 | Wire extractor + verifier (B) into the runner | B + C, pair |
| 2.3 | **End-to-end smoke run of all 7 conditions on 2 dev queries** | C |
| 2.4 | Lock pilot decisions in `docs/decisions.md`: model, retriever, reranker yes/no | all |
| 2.5 | **Double annotation of a shared subset + Cohen's κ** → `reports/agreement.md`. If κ < 0.5 on strength, collapse to direct-vs-hedged per the risk table | B drives; A and C are the second annotators |
| 2.6 | Annotate 10 of the 24 test queries | all three, 2 h/day each |
| 2.7 | Tool-calling metrics on the 40 frozen states + 20 faults | C |
| 2.8 | Challenge-set run: corruption-detection and false-alarm rate | B |

**Gate (Tue 27, evening):** all seven conditions produce a valid `Graph` on all 6 dev queries.

---

### Phase 3 — Dev-set results · Wed 28 → Thu 29 Oct

| # | Task | Owner |
|---|---|---|
| 3.1 | Full dev sweep: B0, B1, B2, M on 6 dev queries, logged | C |
| 3.2 | Human support judgements on dev edges, **blind** (shuffled edges, condition hidden) | all three |
| 3.3 | Compute UER and strength inflation **by hop** for B1 → first RQ1 signal | B + C |
| 3.4 | Compute M vs B1 on dev → first RQ2 signal, with the recall guard (H2d) | B + C |
| 3.5 | Retrieval metrics table with and without reranker | A |
| 3.6 | Figures: UER-by-hop bar chart; one qualitative example graph (static Graphviz export) | A |
| 3.7 | Failure analysis: 5 worst dev cases, categorised | all |

Treat every number from Phase 3 as **dev-set, directional only**. Say so explicitly in the
report — the test set is still unannotated and must stay frozen.

---

### Phase 4 — Freeze & write · Fri 30 Oct

| # | Task | Owner |
|---|---|---|
| 4.1 | Mid report: what is built, pilot decisions, dev results, deviations from the proposal, revised risk register, remaining 4-week plan | all (B leads prose, A leads figures, C leads tables) |
| 4.2 | `README.md`: architecture diagram, how to reproduce, directory map | C |
| 4.3 | Reproducibility check: fresh clone → `make setup && make test && make run-dev` | A |
| 4.4 | Tag `v0.1-midsub`, attach `MANIFEST.md`, `reports/*`, `docs/decisions.md` | C |

---

## 3. Mid-submission deliverables (the Oct 30 definition of done)

1. Frozen corpus v1 + manifest (target ≥ 900 articles, ≥ 60 official docs)
2. Retriever chosen, with pilot numbers; reranker numbers alongside
3. Model chosen, with pilot numbers across all five tasks
4. Edge schema + annotation guide v1 + Cohen's κ on a shared subset
5. 6 dev + ≥ 10 test queries with reviewer evidence graphs
6. All seven conditions runnable end-to-end from one code path
7. **UER and strength inflation by hop, on dev, for B1 vs M** — the headline slide
8. Tool-calling validity, next-action accuracy, and safety numbers (corpus-independent, so fully reportable)
9. Compute log, updated risk register, remaining-four-weeks plan

**Explicitly deferred past Oct 30:** all 24 test queries annotated; frozen test runs;
B1-R and the two ablations at full scale; interactive graph UI; blind scoring at scale;
repeated-sampling stability check.

---

## 4. Compute and time budget

| Resource | Budget to Oct 30 | Used for |
|---|---|---|
| MacBook Air M5, 16 GB | the default | corpus, parsing, BM25, annotation, metrics, **both pilots**, prompt iteration at 4-bit via MLX |
| Kaggle 2×T4 (30 GPU-h/week) | **≤ 20 GPU-h total**, keep ≥ 10 h headroom | embeddings (A7), reranker (A9), the Phase 3 dev sweep under vLLM |
| Colab free T4 | debugging only | short sessions |
| Paid API | ₹0 unless the pilot fails | Haiku 4.5 adapter already behind the same interface (C1), so switching costs nothing |

Dev sweep cost estimate: 6 queries × ~89K tokens for M ≈ 0.5M tokens per pass; ~2–4 GPU-h
per full sweep. Budget three sweeps. Keep `reports/compute_log.md` current from day one —
it is a graded artefact.

Person-time: ~5 h/day each on weekdays, ~6 h on the weekend ≈ **175 person-hours** total.
Phase 2 pairing and shared annotation consume ~35 h of that, so plan ~45 h of solo track
work per person.

---

## 5. Git workflow

- `main` protected. Everything through a PR with one review. Nobody pushes to `main`.
- Branches: `a/<slug>`, `b/<slug>`, `c/<slug>` — e.g. `a/bm25-index`, `b/verifier-rules`.
- **Commit at least once a day per person, even WIP.** The parallel history is itself
  evidence of a three-person contribution; a single 11-day commit is not.
- Merge your own track's PRs the same day. Never let a branch live more than 48 h.
- **In git:** all code, `configs/`, `docs/`, `reports/`, `data/eval/` (queries, gold graphs,
  challenge set, agent states, safety prompts — small and precious), `data/processed/MANIFEST.md`,
  `data/aliases.yaml`, `data/series/*.csv`.
- **Not in git** (`.gitignore`): `data/raw/`, `data/interim/`, `data/processed/*.jsonl`,
  FAISS indexes, `runs/`, model weights, `.venv/`. Share the frozen corpus by zip +
  sha256 recorded in `MANIFEST.md`.
- Daily 15-min standup, same time each day: what merged, what is blocked, who needs whose interface.
- Tag `v0.1-midsub` on Oct 30 and never force-push over it.

---

## 6. Risks over these 11 days

| Risk | Owner | Mitigation |
|---|---|---|
| **Paywalls / archive gaps on ET, Mint, Business Standard** — the single biggest threat | A | Start A1 on Day 1 hour 1. Fallback: lean on BusinessLine + Business Standard + the 60–90 official docs, accept 600–800 articles for mid-sub, and state the shortfall with per-source counts |
| Annotation is the serial bottleneck | B | Dev set only by Oct 30; all three annotate in Phase 2; cut to 4 dev / 16 test per the proposal's risk table if needed |
| Interfaces not frozen → two people idle | all | Phase 0 is non-negotiable and happens in one sitting |
| Verifier labels nearly everything model-inferred | B | Recall guard (H2d) on dev in Phase 3; tune on dev only |
| Too few hop-≥3 edges on dev to see a trend | B | Choose dev queries that admit long chains (oil → import bill → INR → imported inflation); pool deeper hops descriptively |
| Kaggle session limits / quota loss | C | Checkpoint every run to `runs/`; make the sweep resumable per query; keep the laptop path working for all of B0/B1/B2 |
| 2026 news contamination in the candidate models | C | B0 closed-book is already the control; report its UER in the mid report |

---

## 7. Two honest notes on the proposal

1. **Corpus acquisition is understated.** The proposal treats 900–1,200 de-duplicated
   articles across four paywalled publications as a week-1 task. It is the critical path for
   every other track, and no amount of parallelism helps if the corpus is thin. Report
   per-source, per-month counts in the mid report so a shortfall is visible early rather
   than at the end.
2. **The dev set is 6 queries.** Any hop-wise trend seen in Phase 3 will have very wide
   intervals. Present Phase 3 as a working pipeline plus a directional signal, not as
   evidence for H1 or H2 — those need the frozen test runs in week 4.
