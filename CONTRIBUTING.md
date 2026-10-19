# Contributing

Three people, eleven days, one repository. These rules exist so that nobody's
afternoon is spent resolving a merge conflict that a directory boundary would
have prevented.

## 1. Ownership is the conflict-avoidance map

One owner per directory for the whole 11 days (PLAN_MIDSUB.md §1). You may swap
people; do not swap directories.

| Track | Owner | Owns |
|---|---|---|
| **A** | Varun | `scripts/fetch/`, `src/corpus/`, `src/retrieval/`, `data/raw/`, `data/processed/`, `data/series/`, `data/aliases.yaml` |
| **B** | Deepti | `src/schema/`, `src/extract/`, `src/verify/`, `docs/annotation_guide.md`, `data/eval/` |
| **C** | Harshal | `src/llm/`, `src/tools/`, `src/agent/`, `src/conditions/`, `src/eval/`, `configs/`, `notebooks/`, repo infra |

**Nobody edits another track's directory.** If you need a change there, open an
issue with the interface you need and tag the owner. If you are blocked and it
is urgent, say so in the standup — do not reach across and patch it.

### Shared files

`src/schema/models.py` (and the rest of `src/schema/`), `configs/*.yaml`,
`pyproject.toml`, `Makefile`, `.github/`. Announce in the group chat **before**
you touch one, and merge the same day. A shared-file branch that sits overnight
blocks two people.

Changing anything in `src/schema/` also means:

```bash
make schemas   # regenerate docs/schemas/*.json
make test      # the drift test fails if you forget
```

Both the model change and the regenerated schema go in the **same** commit.

## 2. Branches and PRs

- `main` is protected. **Nobody pushes to `main`.** Enforcement is client-side: a
  tracked `pre-push` hook refuses it. Run `make hooks` on your clone or the guard
  is not there. (Server-side protection needs GitHub Pro on a private repo - free
  via the Student Developer Pack, see `docs/decisions.md` D-13.)
- Branch names are `a/<slug>`, `b/<slug>`, `c/<slug>` — `a/bm25-index`,
  `b/verifier-rules`, `c/conditions-runner`. The letter is your track.
- Everything goes through a PR with **one review**.
- **Merge your own track's PRs the same day.** Never let a branch live more than
  48 hours; rebase or merge `main` into it daily if it must.
- Squash-merge, so `main` reads as one commit per unit of work.

```bash
git switch -c b/verifier-rules
# ... work ...
make lint && make test
git push -u origin b/verifier-rules
gh pr create --fill
```

## 3. Commit at least once a day, each

Even work in progress. The parallel history is itself the evidence of a
three-person contribution; a single eleven-day commit is not, and it is what the
grader sees first.

Commit messages: `<track>: <what changed>` — `b: reject asserted edges with no
span`, `a: add PPAC PDF fetcher`. Say what changed, not "updates".

## 4. What goes in git

**In:** all code, `configs/`, `docs/`, `reports/`, `data/eval/` (queries, gold
graphs, challenge set, agent states, safety prompts — small and precious),
`data/processed/MANIFEST.md`, `data/aliases.yaml`, `data/series/*.csv`,
`tests/fixtures/`.

**Out** (see `.gitignore`): `data/raw/`, `data/interim/`, `data/processed/*.jsonl`,
FAISS indexes, `runs/`, model weights, `.venv/`.

Share the frozen corpus as a zip with its sha256 recorded in
`data/processed/MANIFEST.md`. Do not commit the payload, and do not work around
`.gitignore` with `git add -f`.

## 5. Before you push

```bash
make lint      # ruff + black --check
make test      # must be green
```

Run `make hooks` once after `make setup` and pre-commit does most of this for
you. The gate for Phase 1 is `make test` passing **on all three laptops**.

## 6. Tests

- New rules in `src/verify/` and new tools in `src/tools/` need unit tests in the
  same PR. Both are pure enough that there is no excuse.
- Build against `tests/fixtures/`, never the real corpus. Tracks B and C must
  stay runnable before the corpus freeze, and a test that needs `data/raw/` is a
  test that only one laptop can run.
- Anything that needs a GPU, the network or the real corpus gets
  `@pytest.mark.slow` so `make test` stays fast.
- Fixtures are generated: edit `scripts/build_fixtures.py`, re-run it, and commit
  the regenerated files. Do not hand-edit `tests/fixtures/*.jsonl` — the char
  offsets will stop matching and the verbatim-span check will silently rot.

## 7. Dependencies

`pyproject.toml` keeps the runtime surface small on purpose: `pydantic` and
`pyyaml`, plus dev tools. Anything heavy (torch, vLLM, FAISS, MLX, PDF parsing)
goes in the `heavy` extra. Moving something out of `heavy` into the main
dependency list is a shared-file change — announce it, because it lands on all
three laptops.

```bash
uv add --optional heavy some-package   # Phase 1 dependency
uv sync --extra dev                    # what make setup runs
```

Commit `uv.lock` with the change.

## 8. Decisions

Every `[needs pilot]` and `[needs TA decision]` item lives in
[docs/decisions.md](docs/decisions.md) as an open row. When a pilot settles one,
**edit the row in the same PR as the evidence** — give the number and link the
report. An unresolved row on 30 October is a thing we say out loud in the mid
report, not a thing we quietly forget.

## 9. Standup

15 minutes, same time every day: what merged, what is blocked, who needs whose
interface. Interface changes get announced here before they land.
