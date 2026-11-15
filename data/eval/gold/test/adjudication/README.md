# Adjudication protocol — the test gold graphs (#38)

Two people, 10 edges each, independently. Budget about 25 minutes.

```bash
python scripts/prepare_adjudication.py --set test --annotators Deepti Harshal   # already run
# ... each person fills their own CSV ...
python scripts/score_adjudication.py --sheets data/eval/gold/test/adjudication
```

The protocol is the dev one (`../../dev/adjudication/README.md`) — same rules,
same four columns, same D-26 direction test. Read that file for the rules and
this one for what is different about the test half.

## The rules of the exercise

1. **Fill your own file only.** Open the other one when yours is finished and
   committed, not before.
2. **Do not read `../ADJUDICATION.md` first.** It prints the drafter's own
   labels. Reading them turns your agreement with the other annotator into
   agreement with the draft, and κ then measures how persuasive the draft was
   rather than how reliable the annotation is. It is there for the comparison
   *afterwards*.
3. **D-26 is the test.** A span that asserts a relation, or describes a
   mechanism, without stating **which way the destination moves** does not back
   a gold edge. Four of the twenty dev drafts were dropped on exactly that.

## What is different here

**The half is two queries, not four.** `test-cpi-why` is excluded by D-27 and
`test-cpi-effects` by D-27a; neither has a graph, and that absence is a finding
rather than unfinished work. Both remaining queries are anchored on
`FPI_FLOWS` with the same 20 April 2026 cutoff.

**The two graphs overlap heavily.** Four of five edges in each cite the same
two passages, because a "why" and an "effects" question on the same anchor and
cutoff draw on the same coverage. D-26 settled that two query graphs may cite
one passage. **Judge each edge on its own anyway** — you are labelling edges,
not passages, and `tw2`/`te2` carry an identical span in different graphs on
purpose.

**Three edges per graph share one sentence.** `tw3`/`tw4`/`tw5` (and
`te3`/`te4`/`te5`) come from *"A sustained depreciation in the rupee would
directly inflate the import bill, widen both the current account deficit and
fiscal deficit, and feed broader inflationary pressure through fuel and freight
costs."* Their spans are nested: each extends to the destination it claims. The
question to ask on each is whether that destination's own move is **stated**
rather than carried along by a shared verb. The fiscal leg in particular shares
"widen" with the current-account leg.

**Expect to reject some.** The drafter's notes flag the calls it could not
make: whether "on account of" in `tw1` attributes the rupee's pressure to FPI
selling or merely lists it, and whether `tw2`/`te2`'s debt outflows and yield
rise in the same window support a correlational edge or none at all. Dropping
an edge is a result, not a failure — but a graph that falls below four edges
stops being usable as a reference graph, so record *why* in your notes.

## After scoring

Nothing here is a reference set until **both** sheets are committed, the
disagreements are reconciled under one written rule, and a
`review_receipt.json` is signed in `data/eval/gold/test/`. Until that receipt
exists, scoring any run with `--references` against this directory stays
refused, and the graphs' own `notes` field says `DRAFT, NOT ADJUDICATED`.
