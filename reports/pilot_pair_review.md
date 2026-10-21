# Machine-curated retrieval pilot pairs: pending human review

Created 22 October 2026 for Varun’s A8/A9 retrieval work. **These are machine-curated positive evidence pairs, not independently annotated gold.** No pilot decision can be treated as frozen on the basis of this file. Query wording and positive passages were selected together after inspecting the real collected corpus, before comparing retrieval configurations.

`reports/retriever_pilot_pairs.jsonl` contains 20 distinct questions, as-of dates, and real passage IDs compatible with `retrieval.pilot.EvidenceQuery`. Status for every row: **pending human review**. The short anchors below were checked verbatim in their cited passage; they support review of the pairing, not a completed provenance/strength annotation.

## Corpus snapshot originally inspected

- Original file, preserved locally: `data/interim/initial_development/articles.jsonl`; SHA256 `63aa2e5e59c501d5b8441698a2bf0b156483f42638b6bc9cc061effb515cfe59`.
- 664 real passages from 35 documents; paired evidence comes from 17 documents.
- The available snapshot covers March 2026 only. These pairs span different March mechanisms and publication dates, **not** all eight planned anchor episodes or March–September coverage. Replace or extend them once April–September evidence is collected.
- News coverage is concentrated in Economic Times, with two Mint documents and one official CPI release. This is a convenience sample with topic/source/date concentration.
- Only known positive passages are listed. Other valid evidence may exist, particularly after corpus expansion; absence from this list does not mean a passage is irrelevant. Recall/MRR are diagnostic against these incomplete positives.
- Keep model choice and retrieval configuration hidden while a human checks relevance and looks for additional positives. Freeze reviewed pairs and corpus hashes before running the four-way selection pilot. Do not tune these pairs to retrieved rankings.
- All as-of dates are the latest publication date of the selected positives. No URL-derived date or sitemap lastmod was used. The date-level convention matches the frozen Passage contract; it does not implement intraday cutoffs.

## Pair-by-pair review

### a8-curated-01 — oil prices → twin deficits → currency pressure

Why did rising oil costs put pressure on the Indian currency through the fiscal and external balances on 12 March?

As-of: 2026-03-12. Status: **pending human review**.

The paragraph explicitly links import dependence, widening fiscal/current-account deficits and pressure on the rupee; preserve its risk language.

- `mint-820a071eb59246e8f4e4#p3` — [mint: Indian rupee hits record low of 92.35 against US dollar on surge in crude oil prices amid US-Iran war | Stock Market News](https://www.livemint.com/market/stock-market-news/indian-rupee-hits-record-low-of-92-35-against-us-dollar-on-surge-in-crude-oil-prices-amid-us-iran-war-11773294145996.html), published 2026-03-12T11:14:20+05:30.

Verbatim review anchors: “risk of widening twin deficits”.

### a8-curated-02 — oil/US Treasuries → Indian bond prices

What explanations were given for the Indian sovereign bond selloff on 12 March?

As-of: 2026-03-12. Status: **pending human review**.

This paragraph identifies both the oil-price spike and US Treasury slump as triggers; the adjacent yield level alone is not an explanation.

- `mint-820a071eb59246e8f4e4#p7` — [mint: Indian rupee hits record low of 92.35 against US dollar on surge in crude oil prices amid US-Iran war | Stock Market News](https://www.livemint.com/market/stock-market-news/indian-rupee-hits-record-low-of-92-35-against-us-dollar-on-surge-in-crude-oil-prices-amid-us-iran-war-11773294145996.html), published 2026-03-12T11:14:20+05:30.

Verbatim review anchors: “oil prices and a slump in US Treasuries”.

### a8-curated-03 — dollar/FII outflows → rupee weakness

Which overseas capital and dollar developments were associated with the rupee crossing 93 on 20 March?

As-of: 2026-03-20. Status: **pending human review**.

The opening paragraph names a stronger dollar and continuing FII outflows alongside the new intraday rupee low.

- `mint-c1df25e0c50268c643e7#p0` — [mint: Rupee in free fall, down 60 paise to new all-time low of 93.49 against US dollar | Mint](https://www.livemint.com/focus/rupee-in-free-fall-down-60-paise-to-new-all-time-low-of-93-49-against-us-dollar-11773990788094.html), published 2026-03-20T12:43:07+05:30.

Verbatim review anchors: “the greenback strengthened further and FII outflows continued”.

### a8-curated-04 — crude input costs/fixed pump prices → refining margins

How were higher crude procurement costs affecting Indian refiners while retail fuel prices stayed fixed on 17 March?

As-of: 2026-03-17. Status: **pending human review**.

Two paragraphs establish the higher acquisition cost and inability to pass it through; together they support the margin-squeeze mechanism.

- `economic_times-2ed9a34941af97415702#p0` — [economic_times: Oil shock crushes refiners’ margins, threatens growth as crude nears $137](https://economictimes.indiatimes.com/industry/energy/oil-gas/oil-shock-crushes-refiners-margins-threatens-growth-as-crude-nears-137/articleshow/129628742.cms), published 2026-03-17T14:53:00+05:30.
- `economic_times-2ed9a34941af97415702#p2` — [economic_times: Oil shock crushes refiners’ margins, threatens growth as crude nears $137](https://economictimes.indiatimes.com/industry/energy/oil-gas/oil-shock-crushes-refiners-margins-threatens-growth-as-crude-nears-137/articleshow/129628742.cms), published 2026-03-17T14:53:00+05:30.

Verbatim review anchors: “The spike is eating into margins”; “forcing state-run oil companies to absorb the shock”.

### a8-curated-05 — crude → current-account deficit

What current-account sensitivity to a ten-dollar increase in average crude prices was reported by ICRA on 17 March?

As-of: 2026-03-17. Status: **pending human review**.

The paragraph states a conditional 30–40 basis-point deficit widening estimate; it is a reported estimate, not an observed macro outcome.

- `economic_times-2ed9a34941af97415702#p7` — [economic_times: Oil shock crushes refiners’ margins, threatens growth as crude nears $137](https://economictimes.indiatimes.com/industry/energy/oil-gas/oil-shock-crushes-refiners-margins-threatens-growth-as-crude-nears-137/articleshow/129628742.cms), published 2026-03-17T14:53:00+05:30.

Verbatim review anchors: “widen India’s current account deficit by 30–40 basis points”.

### a8-curated-06 — war premiums/rerouting → freight costs

Why were tanker freight charges climbing during the regional oil disruption reported on 18 March?

As-of: 2026-03-18. Status: **pending human review**.

The first paragraph names war-risk pricing and longer routes; the next gives vessel-class cost changes as corroboration.

- `economic_times-41c2a60142623217887a#p6` — [economic_times: Asian refining margins slip into negative territory as Iran war disrupts crude flows](https://economictimes.indiatimes.com/industry/energy/oil-gas/asian-refining-margins-slip-into-negative-territory-as-iran-war-disrupts-crude-flows/articleshow/129651909.cms), published 2026-03-18T14:27:00+05:30.
- `economic_times-41c2a60142623217887a#p7` — [economic_times: Asian refining margins slip into negative territory as Iran war disrupts crude flows](https://economictimes.indiatimes.com/industry/energy/oil-gas/asian-refining-margins-slip-into-negative-territory-as-iran-war-disrupts-crude-flows/articleshow/129651909.cms), published 2026-03-18T14:27:00+05:30.

Verbatim review anchors: “shipping companies impose war risk premiums”; “Freight on larger Suezmax vessels has risen”.

### a8-curated-07 — fuel costs → demand softness → refining margins

How was weaker Asian fuel demand feeding into refinery profitability on 18 March?

As-of: 2026-03-18. Status: **pending human review**.

The two paragraphs report weaker consumption/activity followed by lower product cracks and margins. Preserve the regional rather than India-only scope.

- `economic_times-41c2a60142623217887a#p13` — [economic_times: Asian refining margins slip into negative territory as Iran war disrupts crude flows](https://economictimes.indiatimes.com/industry/energy/oil-gas/asian-refining-margins-slip-into-negative-territory-as-iran-war-disrupts-crude-flows/articleshow/129651909.cms), published 2026-03-18T14:27:00+05:30.
- `economic_times-41c2a60142623217887a#p14` — [economic_times: Asian refining margins slip into negative territory as Iran war disrupts crude flows](https://economictimes.indiatimes.com/industry/energy/oil-gas/asian-refining-margins-slip-into-negative-territory-as-iran-war-disrupts-crude-flows/articleshow/129651909.cms), published 2026-03-18T14:27:00+05:30.

Verbatim review anchors: “weighing on product cracks”.

### a8-curated-08 — crude → global growth/inflation

What global inflation and growth effects did Gita Gopinath discuss if oil averaged 85 dollars in 2026?

As-of: 2026-03-16. Status: **pending human review**.

The quoted scenario states conditional global effects; it must not be represented as a forecast made by this project or as Indian CPI evidence.

- `economic_times-e7f0eb716c799010ef57#p2` — [economic_times: Oil price surge could lift global inflation by 60 bps, trim 2026 growth: Gita Gopinath](https://economictimes.indiatimes.com/industry/energy/oil-gas/oil-price-surge-could-lift-global-inflation-by-60-bps-trim-2026-growth-gita-gopinath/articleshow/129599733.cms), published 2026-03-16T09:02:00+05:30.

Verbatim review anchors: “Headline inflation could rise by 60 bps”.

### a8-curated-09 — logistical disruption → export-credit relief

Why did the RBI retain the longer export-credit window through June 2026?

As-of: 2026-03-31. Status: **pending human review**.

The regulator is quoted citing continuing West Asia logistics disruption; a second paragraph records stakeholder difficulties meeting realisation timelines.

- `economic_times-576bd07acff8f304cfda#p0` — [economic_times: RBI extends export credit window to June 30 amid West Asia disruptions](https://economictimes.indiatimes.com/industry/banking/finance/banking/rbi-extends-export-credit-window-to-june-30-amid-west-asia-disruptions/articleshow/129930362.cms), published 2026-03-31T20:51:00+05:30.
- `economic_times-576bd07acff8f304cfda#p2` — [economic_times: RBI extends export credit window to June 30 amid West Asia disruptions](https://economictimes.indiatimes.com/industry/banking/finance/banking/rbi-extends-export-credit-window-to-june-30-amid-west-asia-disruptions/articleshow/129930362.cms), published 2026-03-31T20:51:00+05:30.

Verbatim review anchors: “continuing logistical disruptions due to the West Asia crisis”; “challenges in meeting export realisation timelines”.

### a8-curated-10 — refinery compatibility → substitute-crude premiums

Why did premiums for heavy sour crude substitutes rise while Asian refiners could not freely switch to lighter alternatives?

As-of: 2026-03-20. Status: **pending human review**.

The source explains that many Asian refineries are optimized for heavy, sour grades and cannot switch to lighter alternatives. It then links compatibility to additional demand and higher premiums for Johan Sverdrup and Mars.

- `economic_times-710fadde2bd93418aac6#p14` and `economic_times-710fadde2bd93418aac6#p15` — [original article](https://economictimes.indiatimes.com/industry/energy/oil-gas/strait-of-hormuz-shock-sends-crude-premiums-soaring-as-refiners-scramble-for-supply/articleshow/129699643.cms), published 2026-03-20T17:06:00+05:30.

Verbatim review anchors: “cannot switch to lighter, sweeter alternatives”; “further boosted premiums”.

The original forex-cap pair was removed after a version-date audit found the fetched copy had been revised on 29 March, after its 28 March query cutoff. This exclusion follows temporal integrity, not retrieval performance. The first smoke report is superseded. Pair-file hashes change after this correction.

### a8-curated-11 — crude imports/prices → petroleum trade deficit

How did Systematix link the disruption in crude import volumes and prices to India’s petroleum trade balance in March?

As-of: 2026-03-20. Status: **pending human review**.

The paragraph explicitly connects lower import volumes plus higher prices with the estimated trade-deficit widening; retain the estimate qualifier.

- `economic_times-6fa68c0d05795a02a037#p11` — [economic_times: India's crude imports took a big hit due to the West Asia Crisis: Systematix Research](https://economictimes.indiatimes.com/industry/energy/oil-gas/indias-crude-imports-took-a-big-hit-due-to-the-west-asia-crisis-systematix-research/articleshow/129694578.cms), published 2026-03-20T12:34:00+05:30.

Verbatim review anchors: “coupled with rising prices”.

### a8-curated-12 — oil → inflation/rate expectations → gold

Why did analysts say high oil prices and inflation concerns were limiting gold during the week ending 20 March?

As-of: 2026-03-20. Status: **pending human review**.

The first paragraph names persistent inflation and elevated US rates; the quote in the second discusses cautious policy and limited gold upside.

- `economic_times-6fd0b395a8039cd42ddb#p3` — [economic_times: Gold falls 5%, silver dips 12% in a week amid strong dollar, inflation concerns](https://economictimes.indiatimes.com/industry/cons-products/fashion-/-cosmetics-/-jewellery/gold-falls-5-silver-dips-12-in-a-week-amid-strong-dollar-inflation-concerns/articleshow/129686178.cms), published 2026-03-20T00:20:00+05:30.
- `economic_times-6fd0b395a8039cd42ddb#p5` — [economic_times: Gold falls 5%, silver dips 12% in a week amid strong dollar, inflation concerns](https://economictimes.indiatimes.com/industry/cons-products/fashion-/-cosmetics-/-jewellery/gold-falls-5-silver-dips-12-in-a-week-amid-strong-dollar-inflation-concerns/articleshow/129686178.cms), published 2026-03-20T00:20:00+05:30.

Verbatim review anchors: “reinforcing bets that US interest rates will stay elevated”; “limiting upside in gold”.

### a8-curated-13 — replacement-crude demand → tanker freight

How did Asian purchases of replacement US crude spill over into freight rates on 20 March?

As-of: 2026-03-20. Status: **pending human review**.

The paragraph connects demand to send US barrels east with rising Aframax freight rates, rather than merely listing physical crude premiums.

- `economic_times-710fadde2bd93418aac6#p8` — [economic_times: Strait of Hormuz shock sends crude premiums soaring as refiners scramble for supply](https://economictimes.indiatimes.com/industry/energy/oil-gas/strait-of-hormuz-shock-sends-crude-premiums-soaring-as-refiners-scramble-for-supply/articleshow/129699643.cms), published 2026-03-20T17:06:00+05:30.

Verbatim review anchors: “That demand to send barrels East has bled into freight rates”.

### a8-curated-14 — Hormuz constraints → Russian crude purchases

How did constrained Hormuz oil flows change Indian refiners’ Russian crude purchases in early March?

As-of: 2026-03-20. Status: **pending human review**.

The paragraph explicitly attributes a sharp increase in Russian purchases to choked Hormuz flows and supplies a magnitude.

- `economic_times-4d5e5baf3380c97e2cda#p13` — [economic_times: A war in West Asia without winners — except may be Russia’s oil machine](https://economictimes.indiatimes.com/industry/energy/oil-gas/iran-war-israel-us-attacks-lng-plant-fire-energy-crisis-crude-oil-price-a-war-in-west-asia-without-winners-except-may-be-russias-oil-machine/articleshow/129695544.cms), published 2026-03-20T15:02:00+05:30.

Verbatim review anchors: “With Hormuz flows choked”.

### a8-curated-15 — repo easing → deposit repricing/customer retention

Why were banks reluctant to lower existing deposit rates fully after the repo-rate easing cycle discussed on 25 March?

As-of: 2026-03-25. Status: **pending human review**.

The first paragraph measures incomplete transmission; the second explains reluctance through the possibility of depositors switching investments.

- `economic_times-b5c173b0dae7aefcab65#p0` — [economic_times: Bank deposits yet to fully reflect repo rate cuts](https://economictimes.indiatimes.com/industry/banking/finance/banking/bank-deposits-yet-to-fully-reflect-repo-rate-cuts/articleshow/129786290.cms), published 2026-03-25T01:14:00+05:30.
- `economic_times-b5c173b0dae7aefcab65#p1` — [economic_times: Bank deposits yet to fully reflect repo rate cuts](https://economictimes.indiatimes.com/industry/banking/finance/banking/bank-deposits-yet-to-fully-reflect-repo-rate-cuts/articleshow/129786290.cms), published 2026-03-25T01:14:00+05:30.

Verbatim review anchors: “customers to shift funds to alternative investment avenues”.

### a8-curated-16 — crude/fixed pump prices → OMC margins

Why did Nomura expect oil-retailer marketing margins to stay negative despite the March excise-duty reduction?

As-of: 2026-03-30. Status: **pending human review**.

Both paragraphs explicitly give the input-cost versus fixed-retail-price mechanism for continuing losses after the duty cut.

- `economic_times-d51045c797c103003169#p1` — [economic_times: Excise duty cut fails to offset oil marketing companies' losses amid rising crude prices: Nomura](https://economictimes.indiatimes.com/industry/energy/oil-gas/excise-duty-cut-fails-to-offset-oil-marketing-companies-losses-amid-rising-crude-prices-nomura/articleshow/129892901.cms), published 2026-03-30T11:47:00+05:30.
- `economic_times-d51045c797c103003169#p4` — [economic_times: Excise duty cut fails to offset oil marketing companies' losses amid rising crude prices: Nomura](https://economictimes.indiatimes.com/industry/energy/oil-gas/excise-duty-cut-fails-to-offset-oil-marketing-companies-losses-amid-rising-crude-prices-nomura/articleshow/129892901.cms), published 2026-03-30T11:47:00+05:30.

Verbatim review anchors: “sharp increase in crude oil prices while pump prices have largely remained unchanged”; “retail pump prices have been kept stable”.

### a8-curated-17 — CPI weights → petrol-price pass-through sensitivity

How did the revised CPI basket make a petrol-price rise more influential according to the ICICI Bank report on 26 March?

As-of: 2026-03-26. Status: **pending human review**.

The paragraph contrasts reduced food weight with higher energy weight and explicitly describes doubled petrol-price impact; this is a reported interpretation of the new basket.

- `economic_times-da68fe7d2aefa5b467c2#p3` — [economic_times: Energy price pressures to drive CPI inflation to 4.5% in FY27: ICICI Bank report](https://economictimes.indiatimes.com/industry/banking/finance/banking/energy-price-pressures-to-drive-cpi-inflation-to-4-5-in-fy27-icici-bank-report/articleshow/129815701.cms), published 2026-03-26T09:54:00+05:30.

Verbatim review anchors: “a price hike in case of petrol now would have twice the impact than before”.

### a8-curated-18 — ethanol blending → crude imports/import bill

What import-saving mechanism did the ethanol industry propose as oil prices rose in March?

As-of: 2026-03-23. Status: **pending human review**.

The industry quote proposes proportionally reducing crude imports through blending above 20%; the policy paragraph gives the import-bill motivation. It is a proposal, not a measured saving.

- `economic_times-f5333db210888cf9a111#p1` — [economic_times: Ethanol industry ready to supply more than 20 pc blending, can cut crude import bill: AIDA](https://economictimes.indiatimes.com/industry/energy/oil-gas/ethanol-industry-ready-to-supply-more-than-20-pc-blending-can-cut-crude-import-bill-aida/articleshow/129737705.cms), published 2026-03-23T00:12:00+05:30.
- `economic_times-f5333db210888cf9a111#p3` — [economic_times: Ethanol industry ready to supply more than 20 pc blending, can cut crude import bill: AIDA](https://economictimes.indiatimes.com/industry/energy/oil-gas/ethanol-industry-ready-to-supply-more-than-20-pc-blending-can-cut-crude-import-bill-aida/articleshow/129737705.cms), published 2026-03-23T00:12:00+05:30.

Verbatim review anchors: “which will reduce proportionally the import of crude”; “to cut fuel import bills”.

### a8-curated-19 — Hormuz closure → oil prices → demand destruction

What did Macquarie say a long Strait of Hormuz closure would require oil prices to do to global demand?

As-of: 2026-03-27. Status: **pending human review**.

The conditional quotation explicitly describes prices rising enough to destroy demand if closure persists; do not present the scenario as an observed event.

- `economic_times-3bb3470d87880765e8c4#p7` — [economic_times: Forget $150, oil at $200 is the new grave warning to the world](https://economictimes.indiatimes.com/industry/energy/oil-gas/crude-oil-price-forecast-200-amid-us-israel-iran-war-inflation-economy-impact-macquarie-forget-150-theres-new-grave-warning-to-the-world/articleshow/129839644.cms), published 2026-03-27T12:04:00+05:30.

Verbatim review anchors: “destroy an historically large amount of global oil demand”.

### a8-curated-20 — official CPI level, descriptive control

What February 2026 headline CPI inflation rate and rural–urban split did the 12 March official release report?

As-of: 2026-03-12. Status: **pending human review**.

This is a descriptive official-document retrieval control, not a causal edge or evidence of the March oil shock changing February prices.

- `mospi-5a1b977e356b0b14de7c#p8` — [mospi: Press release of Consumer Price Index on base 2024=100 for February 2026](https://mospi.gov.in/uploads/latestReleases/latest_release_1773310539387_714ce3b5-4644-4aef-b2e3-64433640a9c3_Press_Release_of_CPI_February_2026.pdf), published 2026-03-12 (day precision from the official listing; the PIB mirror states 16:00 IST).

Verbatim review anchors: “3.21%(Provisional)”.

## Corrected corpus and model execution

The query text, dates and 29 positive texts are preserved in the corrected
development comparison. Two paragraph ordinals changed after navigation removal,
and the CPI passage now identifies the identical retained MoSPI source instead
of its PIB mirror. See `reports/pilot_pair_id_migration.json` and the current
corpus hash in `reports/corpus_validation.json`. The corrected full-corpus run
report `reports/pilot_retriever.md` is pending at this checkpoint. The initial comparison is superseded
after query 10's temporal correction; it must not inform a research decision.

The original BAAI BGE-M3 and bge-reranker-v2-m3 models were downloaded at pinned
revisions and exercised on the local MPS GPU. The run report records package
versions, exact corpus/pair/alias hashes, token limits, batch sizes and runtime.
Embeddings use title plus newline plus paragraph, with a 1024-token cap; long
paragraphs can be truncated. Checkpoints validate model/revision/preprocessing
and full input hashes. Identical inputs can reuse vectors after a paragraph
renumbering, while the current corpus supplies dates and provenance.

The pilot caches each configuration's original top 50 eligible candidates and
unloads BGE-M3 before loading the cross-encoder, keeping the two full models
from coexisting on the 16 GB laptop. Reranking uses the same date cutoff.
A real FAISS-versus-exact backend check over the initial 664-passage sample is
recorded separately; it establishes backend agreement, not retrieval quality.

These pairs remain pending independent review, have incomplete positives, and
are concentrated in March. Freeze reviewed evidence and corpus hashes before
using the four-way comparison to resolve D-02 or D-03.
