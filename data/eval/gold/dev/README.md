# Reviewer evidence graphs — the dev four (B4, issue #15)

**Status: not written. This is the one thing blocking every Phase 3 number.**

Four files are required, one per dev query:

| file | query | anchor | as-of |
|---|---|---|---|
| `dev-oil-why.json` | Why were elevated crude prices pressuring the rupee? | BRENT ↑ | 2026-04-08 |
| `dev-oil-effects.json` | What effects of $100 crude were sources discussing? | BRENT ↑ | 2026-04-08 |
| `dev-rupee-why.json` | Why was the record-low rupee expected to feed imported inflation? | INR_USD ↑ | 2026-05-25 |
| `dev-rupee-effects.json` | What effects of the record-low rupee were sources discussing? | INR_USD ↑ | 2026-05-25 |

Each file is a `Graph` (see `docs/schemas/graph.schema.json`) holding **4 to 6
`source_asserted` edges**, each with a verbatim span.

## The rules

1. **Every edge is `source_asserted`.** If no passage states the relation, the
   edge does not belong in the gold graph. Leaving a real link out is correct
   and expected; the gold standard is the set of links a source *states*, not
   the set that is true.
2. **The span is copied, not paraphrased.** Character for character, from the
   passage. `scripts/check_gold_graphs.py` confirms it against the corpus and
   will reject a retyped one.
3. **Nothing published after the as-of date.** The schema refuses it, so a late
   citation fails at load rather than at scoring time.
4. **Strength is what the language says**, not what you believe: `direct` for
   unhedged ("due to", "driven by"), `conditional` for hedged ("could", "may",
   "if"), `correlational` for co-occurrence only ("amid", "as", "after"). The
   five Causal News Corpus tests are in `docs/annotation_guide.md`.
5. **Hops are breadth-first from the anchor** and the schema recomputes them, so
   a wrong `hop` fails at load (D-12).

## How to do it

```bash
# 1. Get the corpus. It is not in git - 18.5 MB, SHA-256 in
#    data/processed/MANIFEST.md. Unzip to data/processed/.
# 2. Retrieve candidate passages for one query:
python -m conditions --queries data/eval/queries_dev.jsonl --conditions B1 --dry-run
# 3. Read them, write the graph, then check it:
python scripts/check_gold_graphs.py            # structure + spans
python scripts/check_gold_graphs.py --require  # fails while any file is missing
```

## Two annotators, not one

Issue #37 (2.5) needs Cohen's κ on a shared subset, so **at least one of these
four must be annotated independently by two people** before scoring. Agreement
measured on a subset one person wrote twice is not agreement.

## Why this cannot be generated

A gold standard written by the system under test measures the system. The spans
have to be read out of the corpus by a person. `src/eval/gold.py` deliberately
validates but cannot write one.
