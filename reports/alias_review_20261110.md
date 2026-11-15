# Alias review for issue #58 — 10 November 2026

Corpus SHA-256: `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
Active alias table SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
The generated coverage table is `reports/alias_coverage.md`.

I read the candidate passages behind the three zero-count variables and the
reported wording mismatches. Two missing forms genuinely name ontology
variables:

| Variable | Passage | Evidence and proposed form |
|---|---|---|
| `AIRLINE_SHARES` | `economic_times-889e909048d7632ba919#p4` | “IndiGo and SpiceJet shares” refers to listed Indian airline shares. The existing forms do not match it. Add that exact phrase if the table is revised. |
| `CPI_FUEL_LIGHT` | `businessline-9109f06a4b23de7ed137#p4` | “fuel component of CPI” explicitly names the CPI fuel component. Add that exact phrase if the table is revised. |

Other candidate text does not justify a broad alias. “Fuel inflation” appears
as a CPI component in some passages but also in generic inflation discussion,
“fuel inflation expectations”, and the verb “fuel inflation”. A substring
alias would overmatch. “Airline stocks” occurs in coverage of European carriers
(`economic_times-8f25fcb7b44a80063c3a#p11`); it does not repair the Indian
worked example. “InterGlobe Aviation” alone can name a company, a share, or
financing activity, so it is not a safe alias for airline shares. Candidate
corporate-bond-spread matches concerned sovereign spreads, repo spreads, or
ordinary uses of “spread”; none named the ontology variable. The rate-hike
phrase in the CPI test feasibility audit concerned the Federal Reserve and ran
opposite to the Indian query's proposed direction. Widening that alias would
not make `test-cpi-why` answerable.

**Disposition.** The two exact forms are correctness candidates, but this
review does not modify the active table. The completed 56-graph development
sweep, its 247 support judgments, the challenge set, and the reported scores
were produced under the pinned table above. Changing the verifier's aliases
now requires a new, versioned run and a fresh review of any changed edges,
as issue #58 and decision D-25 specify. The current scores must retain their
original configuration. Issue #58 remains open until that versioned update
and revalidation are complete or the team explicitly decides to retain the
frozen table with this measured recall ceiling.
