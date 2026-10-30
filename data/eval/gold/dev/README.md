# Reviewer evidence graphs — the dev four (B4, issue #15)

**Status: drafted, span-exact, NOT adjudicated.** All four files exist and pass
`scripts/check_gold_graphs.py` against the v7 corpus. They were drafted
mechanically by `scripts/draft_gold_graphs.py`, which slices every span out of
the real passage text and runs the B6 rule layer before writing. **That is not
the same as a gold standard** - see "Why this cannot be generated" below, which
still applies. The reviewer's sheet is `ADJUDICATION.md`; until it is signed,
every Phase 3 number measured against these is provisional.

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

Issue #37 (2.5) needs Cohen's κ, so **every edge is annotated independently by
two people who have not compared notes**. Agreement measured on a sheet one
person signed twice is not agreement.

The protocol and the blind worksheets are in [`adjudication/`](adjudication/).
Two points about how it is set up:

- **The worksheets carry no labels.** `ADJUDICATION.md` prints the drafter's
  own, so annotating from that file would turn agreement between the two people
  into agreement with the draft, and κ would measure how persuasive the draft
  was. The worksheets hold the span, the two variables and the dates, nothing
  else, under opaque item ids, in a different order for each annotator.
- **Both annotators take all 20 edges, not half each.** Splitting would leave κ
  resting on 4 to 6 items, which supports no claim; double-labelling the whole
  set also means every edge is settled by two people rather than one.

```bash
python scripts/prepare_adjudication.py --annotators Deepti Varun
python scripts/score_adjudication.py --pair deepti varun   # -> reports/adjudication_kappa.md
```

## Why this cannot be generated

A gold standard written by the system under test measures the system. The spans
have to be read out of the corpus by a person. `src/eval/gold.py` deliberately
validates but cannot write one.

The drafts do not repeal this. What `draft_gold_graphs.py` automates is the
mechanical half - locating candidate passages and copying spans exactly - and
the rule layer only confirms that a span is verbatim and that the passage
mentions both variables. It cannot tell whether the passage **asserts** the
relation, which way the causation runs, or whether the strength label matches
the language. Three candidates that passed every rule were dropped by hand for
exactly those reasons: two cited passages that mention both variables while
asserting nothing between them, and one whose causation ran backwards. That is
the work `ADJUDICATION.md` asks for, and it is why the files say
`MACHINE-DRAFTED, NOT YET ADJUDICATED` in their `notes` field.
