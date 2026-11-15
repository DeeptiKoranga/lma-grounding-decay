# Vocabulary normalisation of `worksheet-harshal.csv`

The sheet was delivered in a different vocabulary from the one the loader
accepts. 34 cells were re-encoded without changing any judgement, and **2 were
cleared because re-encoding them would have meant deciding what the author
meant.** This file records every change so the edit is reviewable and
reversible; the sheet as delivered is in commit `ecf0e52`.

## Re-encoded, no judgement changed (34 cells)

| column | delivered | stored | why this is safe |
|---|---|---|---|
| `asserts` | `TRUE` / `FALSE` | `yes` / `no` | One-to-one, no third value in either vocabulary. |
| `verdict` | `KEEP` | `keep` | Case only. |
| `verdict` | `REJECT` | `drop` | `REJECT` is not in `VERDICTS`. Both rows carrying it also carry `asserts=no`, and the schema admits exactly one verdict for an unasserted edge, so `drop` is forced rather than chosen. |
| `strength` | `DIRECT` | `direct` | Case only. |
| `direction` | `POSITIVE` | `up` | Six rows, all with destinations `IMPORT_BILL`, `CURRENT_ACCOUNT_DEFICIT` or `FISCAL_DEFICIT`, whose cited spans state the destination rising ("inflate", "widen"). `POSITIVE` and `up` cannot differ here. |

## Cleared, pending the author (2 cells)

| item | edge | delivered | stored |
|---|---|---|---|
| `a75831a92a` | `FPI_FLOWS -> INR_USD` | `NEGATIVE` | *(blank)* |
| `7870e25658` | `FPI_FLOWS -> INR_USD` | `NEGATIVE` | *(blank)* |

These are the only two rows whose destination is `INR_USD`, and they are the
only two the author marked `NEGATIVE`. That is the ambiguity:

- Read as a sign convention on the destination variable, `NEGATIVE` means
  `INR_USD` **down**, a *stronger* rupee — which contradicts both cited spans
  and would be a direction disagreement with the other annotator.
- Read as a description of the rupee, it means the rupee weakened, which under
  the ontology is `INR_USD` **up** — agreeing with the other annotator and with
  the draft.

The author's own notes say "rupee weakening" and "exchange rate pressure",
which points at the second reading. **That is not enough to write it in.**
`docs/annotation_guide.md` singles out this exact variable — "Upward `INR_USD`
means a weaker rupee" — because it is the one place where a correct economic
reading and a wrong enum value look identical on the page. A gold standard
whose directions were filled in from someone else's inference of intent is not
a gold standard, and D-26 exists precisely to catch a wrong direction.

So the two cells stay blank until the author sets them. The loader refuses the
sheet while they are, which is the correct behaviour: a partly-filled sheet is
not agreement.

## To finish

Open `worksheet-harshal.csv`, put `up` or `down` in `direction` for those two
rows, and run:

    make kappa-test

Nothing else in the sheet needs touching.
