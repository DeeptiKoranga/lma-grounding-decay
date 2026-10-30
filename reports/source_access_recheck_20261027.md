# A1 / A2 source access — re-check, 27 October 2026

Re-examines the four source gaps recorded in
`reports/track_a_remaining_source_gaps.json` (23 October). **No new source
coverage was admitted, and no access control was bypassed.** The earlier
findings stand; this records the re-check so the mid report cites today's
evidence rather than a four-day-old one.

## Findings

| source | result | disposition |
|---|---|---|
| Business Standard | The project's collector receives **HTTP 403 on `robots.txt`** and stops, as its policy requires. The site serves the file to browser clients but not to this client. | **Excluded.** Retrieving it would mean presenting a browser user-agent to defeat that distinction, which is bot-check circumvention. Declined. |
| RBI | **HTTP 418 on `robots.txt`** on both `www.rbi.org.in` and `m.rbi.org.in`. | **Excluded.** Same reason. |
| Mint | Reachable, and `robots.txt` permits `User-agent: *`. A bounded probe (March, 25 requests) discovered 887 archive URLs, admitted **0** of 6 downloads. | **Not expandable.** See below. |
| PIB | `robots.txt` returns HTTP 200 but serves an HTML error page, not a policy document. | **Untested.** The only remaining avenue; needs seed discovery. |

## Why Mint cannot be expanded

The collector rejected all six candidates, correctly, for two distinct reasons:

- **No publication date** — `/fuel-prices`, `/fuel-prices-diesel` are standing
  landing pages. `lastmod` and `dateModified` are not publication dates, and
  admitting them would put undated rows into a corpus whose entire as-of
  discipline depends on real publication dates.
- **No extractable article body** — "possible paywall or extraction failure" on
  four of six, which is what a paywalled or client-rendered article looks like
  to a text extractor.

Two further problems with the Mint archive as a source: a large share of the
sitemap is `/hindi/` content, which the proposal scopes out (English-language
national press only), and the archive URLs carry no date, so sitemap discovery
surfaces out-of-window articles (one probe candidate was dated 27 October).

Yield was 14 candidates from 887 URLs, and 0 admitted. Mint stays at its
existing 12 documents.

## Consequence for the mid report

A1 and A2 are **not advanceable by legitimate automated means**. The corpus
shortfalls are therefore limitations to state, not open work to finish:

- **Business Standard: 0 documents.** Named in the proposal's corpus spec.
- **RBI: 0 documents.** Policy statements and minutes are named in the spec, and
  two of the eight candidate anchor episodes were RBI meetings. Both of those
  episodes are already `no_series` under D-18, so they have neither a
  confirming series nor a primary document, which is why neither survived into
  the query set.
- **Mint: 12 documents**, against a spec naming it as one of four publishers.
- **PIB: 0 documents.**

The corpus is therefore 870 Economic Times and 213 BusinessLine of 1,095 news
documents — heavy single-publisher concentration, which belongs in the
limitations section alongside the Recall@10 of 0.4259.
