# Adjudication protocol — the dev gold graphs (#15, #37)

Two people, 20 edges each, independently. Budget about 45 minutes.

```bash
python scripts/prepare_adjudication.py --annotators Deepti Varun   # already run
# ... each person fills their own CSV ...
python scripts/score_adjudication.py --pair deepti varun
```

## The rules of the exercise

1. **Fill your own file only.** `worksheet-deepti.csv` and
   `worksheet-varun.csv`. Open the other one when yours is finished and
   committed, not before.
2. **Do not read `../ADJUDICATION.md` first.** It prints the drafter's own
   labels. If you read them, your agreement with the other annotator becomes
   agreement with the draft, and the κ measures how persuasive the draft was
   rather than how reliable the annotation is. It is there for the comparison
   *afterwards*.
3. **Do not compare notes while annotating**, including "what did you put for
   the OMC one". That is the single thing that makes the number meaningless, and
   it is not recoverable afterwards.
4. The two sheets hold the same 20 edges **in different orders**, on purpose, so
   a shared run of fatigue or context cannot look like agreement.

## The four columns you fill

| column | values | what it means |
|---|---|---|
| `asserts` | `yes` / `no` | Does this span **state a relation** between `src_var` and `dst_var`? A passage that mentions both without linking them is `no`. |
| `direction` | `up` / `down` / `stable` | Which way does **`dst_var`** move? Leave blank if `asserts` is `no`. |
| `strength` | `direct` / `conditional` / `correlational` | What the **language** says, not what you believe. Leave blank if `asserts` is `no`. |
| `verdict` | `keep` / `fix` / `drop` | `fix` means the relation holds but a label is wrong. `asserts=no` must be `drop`. |

`note` is free text — use it whenever you hesitate. The hesitations are the most
useful output of the evening.

### Strength, concretely

- **`direct`** — unhedged: "caused", "due to", "driven by", "led to", "raises".
- **`conditional`** — hedged: "could", "may", "if", "expected to", "risks".
  Hedging wins: *"may have been caused by"* is conditional, not direct.
- **`correlational`** — co-occurrence only: "amid", "as", "after",
  "associated with". Also reported concern — *"were fuelling worries about"* —
  which is not an asserted move.

Full tests in `docs/annotation_guide.md`.

## Dropping edges is a correct outcome

The gold standard is the set of links a source **states**, not the set that is
true. Three candidates were already dropped by hand before these drafts were
written — two spans that mention both variables while asserting nothing between
them, and one whose causation ran backwards. Expect to find more. An evening
that drops four edges has improved the gold standard, not damaged it.

## What happens to the numbers

`scripts/score_adjudication.py` writes `reports/adjudication_kappa.md`:

- **κ between the two of you**, per dimension, with a 95% interval. The
  pre-declared threshold is **κ ≥ 0.6** on `asserts` and `direction`.
- **A κ-paradox check.** If nearly every edge does assert its relation, chance
  agreement approaches observed agreement and κ collapses *even when you agreed
  on 19 of 20*. The report flags that case and prints the raw agreement beside
  it. Do not quote the κ alone when the flag is set.
- **Agreement with the machine draft**, in a separate section. That is a
  different question — how good the draft was — and must never be quoted as κ.

At n=20 the interval is wide. The report says how wide, from the data, and the
mid report has to carry that rather than a bare point estimate.

## After scoring

1. Reconcile the disagreements together — that conversation is allowed, and
   needed. Disagreements are what `fix` and `drop` rows are for.
2. Apply the agreed changes to the graph files, re-run
   `scripts/check_gold_graphs.py --require`, and regenerate the receipt.
3. Fill in `../review_receipt.json`: `reviewer`, `reviewed_on`,
   `independent_review`, `all_relations_and_strengths_reviewed`. **Only then**
   does `eval.references.validate` accept the set, which is what unblocks #20,
   #42, #43 and #44.
4. Remove `MACHINE-DRAFTED, NOT YET ADJUDICATED` from each graph's `notes`. A
   test asserts that string, so it will fail until you also update the test —
   deliberately, with a diff, which is the point.
