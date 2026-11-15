% Does Grounding Decay with Distance? Measuring and Repairing Weak Links in LLM Causal Explanations of Indian Macroeconomic News
% Language Models & Agents (LMA) Group Project 2026 — Final Report
% [GitHub submission branch](https://github.com/DeeptiKoranga/lma-grounding-decay/tree/b/episode-confirmation) · [Reproduction and demos](https://github.com/DeeptiKoranga/lma-grounding-decay/blob/b/episode-confirmation/README.md)

## Abstract

When a language model explains how one news event led to another, the first
link is often backed by a quoted source. Later links often are not. The answer
reads the same either way, so a reader cannot tell where the evidence ran out.
We ask whether this happens, and whether checking each link and searching for
more evidence fixes it.

Our system answers a dated question with a graph. Every link shows the passage
behind it, which way the effect runs, and how strongly the source states it.
Fixed rules decide whether a passage may be used at all: it must be in our
frozen corpus, published on or before the question's date, mention both
variables, and contain the quoted words exactly. A language model then decides
the separate question of whether the passage says what the link claims. The
system may search for more evidence, up to 12 tool calls.

We ran seven conditions on four development questions under two models. On the
main model our full system's unsupported-link rate was 0.167 lower than
ordinary RAG across three comparable questions, and it found 0.062 more of the
links a human marked correct. It tied with reranked RAG. On deliberately
corrupted links the checker caught 17 of the 38 that fixed rules cannot catch
at all, and wrongly flagged 2 of 23 clean ones. A blind human check agreed with
21 of 27 of the earlier labels.

On the two held-out questions, scored with 291 fresh labels, our system showed
no gain at all and found 12.5 percentage points fewer correct links than
ordinary RAG. That breaks the 10-point recall limit we set in advance (H2d).
With four development and two held-out questions, and almost no evidence at
distant links, every number here describes what we saw rather than proving a
general result.

## 1. Introduction

People increasingly ask assistants to join up events the news reported
separately: an oil shock, a weaker rupee, a central-bank decision. The first
step is usually backed by a retrieved passage. Later steps often rest on the
model's own reasoning. Careful wording in the source, such as "could widen the
deficit", can harden into a flat claim further down the chain. The answer looks
the same throughout, so the reader cannot see where it stopped being grounded.

We work on Indian macro-financial news about crude oil, the rupee, RBI policy
and bond yields, over a frozen corpus running 1 March to 30 September 2026. The
reader we have in mind is a student or non-specialist who wants to check a
dated explanation. We say a link is **supported** when a passage states that
relation, in that direction, and was published in time. We measure whether the
text backs the claim, not whether the economics is true.

**RQ1 (does the problem exist?).** Do unsupported links and overstated causal
strength increase the further a link sits from the original event?

**RQ2 (does our fix work?).** Can a system that builds a graph, checks each
link and searches for missing evidence reduce those problems without throwing
away the useful links it should keep?

**Hypotheses.** H1: in ordinary RAG both problems grow with distance. H2a: our
system has at least 10 points fewer unsupported links than ordinary RAG. H2b:
the growth with distance is smaller for our system. H2c: it beats RAG asked to
label its own links. H2d (recall guard): it finds no more than 10 points fewer
correct links than ordinary RAG.

H2d matters most, and we set it before running anything. A checker can always
improve the unsupported rate by deleting every link it cannot confirm. That
gives a better number and a worse answer. H2d separates repairing an
explanation from gutting it.

## 2. Literature Review

Self-RAG learns when to retrieve and uses reflection tokens to critique a
generation. FIRE interleaves retrieval and verification for fact-checking
claims. CausalRAG uses causal relations to structure retrieval. These motivate
selective retrieval and verification, but they evaluate different units from a
directed, dated edge in a generated economic explanation.
[Self-RAG](https://arxiv.org/abs/2310.11511) ·
[FIRE](https://aclanthology.org/2025.findings-naacl.158/) ·
[CausalRAG](https://aclanthology.org/2025.findings-acl.1165/)

ReCEval evaluates reasoning steps for correctness and informativeness. We use a
weakest-link rule for paths and adapt causal-language labels from Yu, Li and
Wang. Our contribution is to measure provenance and strength by hop under a
fixed publication cutoff, then compare a bounded edge-repair loop against
standard and reranked RAG, with a guard on how much useful evidence survives
verification. [ReCEval](https://aclanthology.org/2023.emnlp-main.622/)

## 3. Dataset Created and Used

**Corpus.** A frozen snapshot of **1,156 documents** (1,095 news, 61 official)
and **16,472 passages**, published 1 March to 30 September 2026 and hash-pinned
in `data/processed/MANIFEST.md`. Economic Times supplies 870 documents,
BusinessLine 213, MOSPI 37, PPAC 14, Mint 12 and eaindustry 10. Business
Standard, RBI and PIB yielded none. Deduplication used exact full-text hashing,
and for news MinHash over title and first-paragraph trigrams at a Jaccard
threshold of 0.85. Every passage carries exact character offsets into its
parent document; without them verbatim span checking would be impossible, and
the whole provenance distinction rests on it.

**Macro series.** Six series, **161 original-vintage observations**, each with
an `available_on` date. A series confirms only that a move happened; it is
never evidence for a causal link. Coverage is uneven: 141 observations are
USD/INR, and FPI flows contribute one.

**Evaluation sets.** Eight anchored queries over four episodes, split four
development and four test **by episode**, so the halves share no event, no date
and no passages. Two test queries have signed reference graphs; Section 8
explains the two exclusions. The four development reference graphs hold 16
source-asserted edges and the two test graphs hold eight. The challenge set
holds 130 items: 23 clean controls and 107 mechanically corrupted edges across
five families. Synthetic diagnostics add 40 frozen agent states, 25 adversarial
safety prompts and 20 tool-fault scenarios. Two public datasets are used as
diagnostics and never for training: Yu et al. (2019) causal language and
FinCausal 2020 task 1, 200 sampled items each.

## 4. Methodology

**The graph.** Each answer is a graph over a **closed ontology of 46
variables** (`BRENT`, `INR_USD`, `CPI_HEADLINE` and so on). Every link carries
a direction, a provenance label and a strength level. The ontology is enforced
in the schema, so a model cannot invent a variable to make a chain look
complete.

A link is `source_asserted` when a passage published by the cutoff states the
relation in that direction — in M and A-NoLoop only the verifier may set this —
and `model_inferred` when no supporting passage was found under the permitted
search. Strength is `direct` for unhedged causal language (caused, due to,
driven by), `conditional` when hedged (could, may, if), and `correlational` for
co-occurrence or sequence alone (amid, as, after).

`hop` is breadth-first distance from the anchor and is recomputed by the schema,
so a mislabelled hop fails at load rather than quietly distorting a hop-sliced
metric.

**Two layers of checking.** Deterministic rules run first and a language model
judges only what survives them. The four rules: the cited passage must be in
the corpus; published on or before the cutoff; mention both variables; and
contain the quoted span word for word. Passing the rules establishes
*eligibility* only. In M and A-NoLoop the verifier then judges support in a
fresh context, without the generator's reasoning, before a link may be marked
`source_asserted`.

**Agent loop.** A controller tracks open links, search counts and remaining
budget. It verifies unverified links first, then searches for evidence on the
most important `model_inferred` link. It stops when the important links are
resolved, when two searches add nothing new, or at 12 tool calls. Six tools —
`search_corpus`, `get_series`, `verify_edge`, `counter_search`, `update_graph`,
`stop` — are schema-validated. The date filter and budget are enforced in code,
not in the prompt. Tools never mutate the corpus or series.

**Metrics.** UER (unsupported established-edge rate) divides unsupported
established links by all established links. A prose claim counts as established
when cited or unhedged. Strength inflation divides supported links stated more
strongly than their source by all supported links. Reference-edge recall counts
matches on source, destination and direction against the signed references. We
compute per query and average over available denominators, comparing matched
query pairs. Gates fixed in advance: ten established edges per hop bucket, all
three buckets for a trend, ten queries for inference. An empty denominator is
reported as unavailable, never as zero.

## 5. Experiment Runs

**Model and compute.** `mlx-community/Qwen3-8B-4bit`, revision `545dc425`,
chosen by the pilot in Section 7.1; the sensitivity arm used a local Qwen3.5-9B
4-bit checkpoint at `8b2b98c`. Both sweeps ran locally through MLX, using 185
model calls and 383,000 tokens over 116.1 minutes of model-call time. A private
two-T4 Kaggle execution used **1.211 allocated GPU-hours**. **No paid API
request was made.**

Seven experiment runs back this report: the two development sweeps (28 graphs
each, seven conditions on four signed queries per arm); held-out generation (14
graphs on the two signed test queries); the 130-item corruption challenge
against both the rule layer and the verifier; retrieval over 20 pilot and 2
signed queries; 400 frozen public-benchmark examples; tool, action and safety
probes over 40 states, 20 faults and 25 prompts; and a three-seed stability
check on one query.

**Held-out generation.** The pinned model completed all seven conditions on
both signed FPI questions, which share one episode and a 20 April 2026 cutoff.
The reference preflight and checksum-bound audit passed, all 14 anchor checks
confirmed the FPI threshold, and none of the 121 logged passage occurrences
crossed the cutoff. A-NoVerify and B2 each produced one non-verbatim citation
span. The runs took 34 model calls and 74 tool calls over 38.2 minutes.

Every condition produced six links on the effects question. On the "why"
question B0, B1 and B1-R produced one link each while B2 and all three full-
system variants produced six, which is the clearest single illustration of what
the graph representation adds over prose.

**Working demo.** `reports/graph_explorer.html` is a self-contained browser
file. A sourced link opens its span, passage ID, publication date and cutoff;
an inferred link shows its unresolved status. It runs locally to respect the
research-use licence on corpus excerpts. The README links a downloadable
synthetic demo and a runnable seven-condition pipeline.

## 6. Ablations

The seven conditions share the pinned model within an arm, plus corpus, cutoff
and queries. Conditions that retrieve share the first-stage retriever. All
seven run through the same pipeline.

**B0** answers from the query alone with no retrieval, as a reference point.
**B1** is standard RAG producing prose with citations, the main baseline.
**B1-R** adds a top-50 cross-encoder reranker, isolating retrieval quality.
**B2** is RAG asked to emit its own provenance and strength labels, the
prompting control. **A-NoVerify** is the full system with the verifier replaced
by self-labels, and **A-NoLoop** is the full system retrieving once with no
agent loop. **M** is the proposed method: graph, labels, verifier, agent loop
and weakest-link paths.

Only M against B1 was pre-declared. The rest are **exploratory** and are not
promoted past that, but they isolate each capability.

| Contrast | Tests | Primary arm | Sensitivity arm |
|---|---|---:|---:|
| M − B2 | **H2c**: beats prompted self-labelling | −0.250 (4 pairs) | −0.625 (2 pairs) |
| M − A-NoVerify | does verification help? | −0.208 (4 pairs) | −0.625 (2 pairs) |
| M − A-NoLoop | does targeted retrieval help? | +0.500 (1 pair) | n/a (0 pairs) |
| B1-R − B1 | does better ranking alone help? | −0.333 (3 pairs) | −0.092 (4 pairs) |
| M − B1-R | does the full system beat reranking? | 0.000 (4 pairs) | −0.125 (2 pairs) |

H2c favours M descriptively in both arms. The A-NoVerify contrast points the
same way, and it is the ablation that matters most: removing the verifier makes
the system worse by the measure the study is built on. **The A-NoLoop figure
should not be read** — it rests on one query, because A-NoLoop established
exactly one link across the whole primary arm and none in the sensitivity arm.
B1-R beat B1 in both arms, and M only tied B1-R on the primary arm. The paired
strength-inflation contrast has no usable denominator in either arm.

Two secondary metrics the proposal asks for had been computed since Phase 2 and
printed nowhere. Provenance accuracy is 0.750 for M, B1 and B1-R, 0.500 for B2
and 0.396 for A-NoVerify. Strict path validity is 0.083 for M, 0.125 for B1-R
and 0.000 for the rest.

**Provenance accuracy audits the instrument itself**, since the provenance
label is what the whole study measures with. M reaches 0.750 against
A-NoVerify's 0.396 in the primary arm, and 0.917 against 0.104 in the
sensitivity arm. The verifier roughly doubles the rate at which a link's label
is right, which defends it more directly than the UER difference does.

**Strict path validity is near zero everywhere** — 0.083 for M, never above
0.125. A path counts only if every hop is established, supported and no
stronger than its source. Almost no multi-hop explanation in this corpus
survives that end to end. That is a finding about the difficulty of the task,
and it is the study's hop-by-hop claim restated at the level of whole paths.

## 7. Evaluations

### 7.1 Model selection, and what it cost

Both candidate models ran 100 identical cases, 20 in each of five tasks. The
rule, recorded before the runs, took the highest unweighted mean and broke ties
within 0.03 on latency. The means tied at exactly 61.0%, so the faster 8B model
won. A later field analysis, which did not change the frozen rule or scores,
shows what that tie concealed.

The selected 8B model named the wrong passage in **17 of 20** citations and
quoted non-verbatim in **10 of 20**; the rejected 9B model did neither, even
once. Strength mismatches were comparable (7 against 6 of 20), but strictly
correct extractions were 1 of 20 against 13 of 20.

The five tasks are not equally important here. Extraction decides whether any
link can be established at all, and the models differ by 60 points on it. A tie
broken on speed selected the model weaker at the thing the architecture most
depends on. The rule was recorded in advance and followed, which is what makes
the consequence visible rather than arguable.

### 7.2 Retrieval

Twenty query–evidence pairs, four configurations, 2,035 pooled relevance
judgements. The rule — take the simplest configuration within 0.03 Recall@10 of
the best — was fixed beforehand.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| BM25 | 0.2405 | 0.3518 | 0.4555 |
| BM25 with alias expansion | 0.2211 | 0.3551 | 0.5787 |
| Hybrid (reciprocal rank fusion) | 0.2958 | 0.4161 | 0.6663 |
| BGE-M3 (selected) | 0.3327 | 0.4259 | 0.6981 |
| BGE-M3 with top-50 cross-encoder | 0.4072 | 0.5296 | 0.7101 |

BGE-M3 leads on Recall@5 among unreranked configurations and on MRR@50, so the
simple rule and the fuller view agree. The judgements are automated, not human,
and are adequate for a development choice only.

A check on the two signed test queries is far less flattering. BGE-M3 reached
Recall@10 of 0.250 and MRR@50 of 0.083; adding the reranker gave 0.000 and
0.026, moving the first signed evidence for the "why" query from rank 6 to rank
19. Two queries cannot establish a general effect, but they warn that the
development pilot may not transfer.

### 7.3 Public benchmarks

The cue list and the pinned model classified the same frozen 200 items per
benchmark.

| Check | Cue baseline | Qwen3-8B |
|---|---:|---:|
| Strength macro-F1 (Yu et al.) | 0.414 | 0.478 |
| Strength accuracy (Yu et al.) | 0.350 | 0.530 |
| Detection F1 (FinCausal) | 0.497 | 0.549 |
| Detection accuracy (FinCausal) | 0.525 | 0.590 |

The model beat the cue baseline on both. This is standalone classification on
public text: neither dataset labels edge direction, and the citation and date
rules sit outside the benchmark.

### 7.4 Building the reference set

Two annotators labelled all 20 drafted development links independently, blind
to the draft and to each other, with sheet order shuffled per annotator.

| Dimension | Items | Raw agreement | Chance | Cohen's kappa |
|---|---:|---:|---:|---:|
| Asserts a relation | 20 | 0.800 | 0.740 | 0.231 |
| Direction | 15 | 1.000 | 1.000 | undefined |
| Strength | 15 | 1.000 | 0.502 | 1.000 |

**The kappa is the wrong summary here, so we report it only beside the raw
agreement.** The annotators agreed on 16 of 20, but "asserts a relation" was
true for 16 and 18 of 20, so chance agreement reaches 0.740 and the coefficient
collapses to 0.231 — the Feinstein and Cicchetti (1990) paradox, caused by a
skewed marginal rather than by disagreement.

All four disagreements were the same case: a span that asserts a relation while
leaving the direction to the reader. One written rule settled them — a
reference link carries a direction, so the span must state which way the
destination moves — and all four were dropped, leaving **16 links, four per
graph**, exactly the declared minimum. Both annotators signed a receipt
carrying a SHA-256 of every reference file and of the corpus, so an edit after
signing invalidates the attestation rather than passing unnoticed. That is what
makes the false-alarm rate below quotable.

![**Figure 1.** The `dev-oil-effects` reference graph after adjudication. The ATF-price-to-airfares link survives on its own evidence, but the crude-to-ATF link that would connect it to the anchor did not, so it sits at hop 2 with no hop-1 parent. This orphaned pair is the chain our proposal used to motivate the study.](figures/gold_dev_oil_effects.png)

### 7.5 Challenge set: what rules catch, and what they cannot

130 items built from both signed halves. Against the rule layer alone, with no
model involved:

| Corruption family | Items | Flagged | Rate |
|---|---:|---:|---:|
| Unsupported intermediate hop | 23 | 23 | 1.000 |
| Wrong date | 23 | 23 | 1.000 |
| Wrong target | 23 | 23 | 1.000 |
| Reversed relation | 23 | 0 | 0.000 |
| Inflated strength | 15 | 0 | 0.000 |
| Clean controls | 23 | 0 | — |

Sixty-nine of 69 citation corruptions caught with zero false alarms, and none
of the 38 semantic ones. The misses are structural: reversing a link leaves the
same two variables in the same passage with the same quoted words, so every
rule still passes, and no rule reads the strength field.

Those 38 are what the verifier exists for, and it was run on them.

| Semantic family | Items | Caught by rules | Caught by the verifier |
|---|---:|---:|---:|
| Reversed relation | 23 | 0 | 9 (0.391) |
| Inflated strength | 15 | 0 | 8 (0.533) |
| **Total** | **38** | **0** | **17 (0.447)** |

False alarms on the 23 clean controls: **2 (0.087)**, against 0 for the rules.
So the verifier moves these families from a structural zero to a little under
half, and pays 2 sound citations for it.

**The better of those two figures deserves suspicion.** The verifier disagreed
with the signed strength on **8 of the 23 clean controls** — a third of links
where nothing was corrupted and the label is right. Inflation detection is
defined as returning a weaker label than claimed, so a verifier that labels
strength noisily scores detections it did not earn. A base disagreement rate of
0.348 against 0.533 on inflated items is a real margin but a thin one, and this
sample cannot separate discrimination from noise. The reversed-relation figure
has no such ambiguity: it is read off provenance, and a control disagreement
there is already counted as a false alarm.

### 7.6 Capability, safety and tool calling

| Metric | Result |
|---|---|
| Next-action accuracy, standalone model choice, 40 states | 0.125 |
| Argument validity (schema and unchanged cutoff) | 0.850 |
| Unsafe-call rate (schema, cutoff **or budget**) | **0.275** |
| Calls proposed in zero-budget states | **5 of 5** |
| Investment-advice leakage, 25 adversarial prompts | 0 |
| Own-forecast leakage, 25 prompts | 0 |
| Post-cutoff evidence use, 25 prompts | 0 |
| Asserted labels without a verbatim span, 25 prompts | 0 |
| Synthetic tool-fault recovery | 20 / 20 |

Three qualifications. The 0.125 is the model's standalone choice on scripted
states; the executed controller uses deterministic priority, so it is not the
running agent's accuracy. The unsafe-call rate is **not** the complement of
argument validity, and the gap is the point: five states have no budget left,
where the only safe action is to stop, and the model proposed a call in **all
five**. Those calls had valid schemas and correct cutoffs, so an earlier
definition scored them all safe at 0.150. Counting the budget gives 0.275.
Finally, the safety screen was reviewed by an assistant, not an independent
human.

### 7.7 Development results and how far the labels can be trusted

Both arms completed 28 graphs each and passed structural audit.

| Arm | B1 UER | M UER | M−B1 UER | M−B1 recall | H2d |
|---|---:|---:|---:|---:|---|
| Primary Qwen3-8B | 1.000 (3/4) | 0.750 (4/4) | −0.167 (3 pairs) | +0.062 (4 pairs) | holds |
| Sensitivity Qwen3.5-9B | 0.529 (4/4) | 0.250 (2/4) | −0.100 (2 pairs) | −0.062 (4 pairs) | holds |

**H1 is not testable on any condition.** A trend needs all three hop buckets at
ten established links each; the best any condition manages is one, and on
several the hop-3-or-deeper bucket is empty — nothing is measured in the slice
RQ1 is about. The primary B1 buckets hold 5, 2 and 1 links; the sensitivity
ones 13, 1 and 0. **H2b has zero usable paired queries** in both arms.

**Where these labels came from.** The 247 support labels behind these figures
were assistant-produced drafts. A stratified blind sample of 40 was then
annotated by an author who did not hold the key and had not produced them.

| Informative rows only | Value |
|---|---:|
| Informative rows | 27 of 40 |
| Claims the human rejected | 14 of 27 |
| Raw agreement | 0.778 |
| Cohen's kappa | 0.560 (95% CI 0.249 to 0.870) |
| Disagreements | 6 of 27 |

Thirteen rows carried no evidence span, so the only available verdict was
*unsupported*; agreement there is agreement by construction and they are
excluded. **Every disagreement falls in the sensitivity arm** — the primary arm
agreed on all 10 informative rows, the sensitivity arm on 11 of 17. The primary
sample held 6 supported and 4 unsupported labels, so chance agreement is 0.52
and its kappa of 1.000 rests on a real denominator rather than a dominant
label. It is still ten rows.

Five of the six disagreements are the assistant crediting support the human
rejected. An over-credited link leaves the UER numerator, so a label set biased
this way *understates* UER: the sensitivity arm's rates may be optimistic.

**The held-out evaluation.** One author reviewed all 30 prose outputs, approved
27 revisions and authored all 291 support judgements for the revised scoring,
attesting to blinding and independence.

| Arm | Judgements | M−B1 UER | M−B1 recall | H2d |
|---|---:|---:|---:|---|
| Held-out | 55 | 0.000 (2 pairs) | **−0.125** (2 pairs) | **fails** |
| Primary development | 122 | −0.167 (3 pairs) | +0.0625 (4 pairs) | holds |
| Sensitivity development | 114 | −0.250 (2 pairs) | 0.000 (4 pairs) | holds |

**H2d fails on the held-out half, and that is the guard working.** We said in
advance that our system should find no more than 10 points fewer correct links
than ordinary RAG. It finds 12.5 points fewer, and the UER gain meant to pay
for that loss is exactly zero. On this half the checker bought nothing and lost
links to get there — the deletion-not-repair failure H2d was written to catch.

Two caveats pull opposite ways and neither rescues it. Two query pairs is far
below the ten-query gate, so the breach is descriptive. But the development
half where H2d holds rests on labels one author produced for a system the team
built, while the only blind-validated evidence is the 40-row sample over the
earlier assistant labels. **The guard holds where the evidence is weakest and
fails where it is freshest.**

**Stability.** Three seeds on one development query produced the same two
established links with byte-identical evidence and a UER of 0.500 each time,
while the proposed link sets varied. The verifier absorbs the generator's
randomness rather than passing it on.

### 7.8 Does verification repair, or does it delete?

The ablations make the mechanism visible. Remove the verifier and the
generator's self-labels establish 36 of 36 links. Keep the verifier but remove
the search loop and 0 of 35 are established. The full system establishes 8 of
35.

Read alone that looks like an over-cautious verifier, and we first read it that
way. The model pilot suggests otherwise: the selected generator fails on
exactly the two fields the rules check, with 17 of 20 citations naming the
wrong passage and 10 of 20 quotations not verbatim, where the rejected
alternative failed neither. If most citations are wrong, a verifier that
rejects them is behaving correctly, and the low establishment rate is largely
an **extraction** failure rather than a **verification** one. The two
observations are independent and they agree.

## 8. Limitations

**What the design cost us.** Of eight candidate anchor episodes, three confirm
as declared and only two against official data: the March oil shock needed
redating because the Brent series holds no March observation, and the September
bond sell-off was dropped because the yield series ends in August. That cut 30
planned queries to 8 and capped the signed reference set at 24 links. The
compounding is easy to hide and worth stating — a sparse series store did not
weaken one measurement, it propagated through anchors to queries to the
reference set to the challenge set, and finally to the hop coverage RQ1 is
defined over.

**The study is too small to answer RQ1.** Four development and two held-out
questions sit far below the ten-query gate we set. Twelve of the 16 development
reference links are at hop 1 and four at hop 2, with none deeper. UER can still
be reported at hop 3 or more because it is measured over generated links, but
reference-edge recall — the H2d guard — has no denominator there. The guard is
unavailable in exactly the slice where H1 predicts grounding is worst.

**Two of the four test questions have no reference graph.** A reachability
audit excluded `test-cpi-why` before anyone read a passage: its target is
paired with headline CPI in exactly one passage on or before the cutoff, that
passage is Federal Reserve coverage rather than Indian, and it runs the wrong
way. `test-cpi-effects` was excluded only after reading. The audit counts
variables that co-occur with the anchor and says so; reading the passages shows
the condition failing structurally, because in this corpus Indian headline CPI
is the *destination* of the oil shock rather than its source, and an effects
graph rooted at CPI cannot use an inbound link. Both exclusions are measured
limits of what the corpus supports, not unfinished work.

**Most support labels are not independently reviewed.** The 247 development
labels behind the historical figures were assistant-produced. The 291 revised
labels were authored by one author of this report, for a system this team
built, with a self-attestation of blinding. The only blind, independent
evidence is the 40-row sample, which covers 27 informative rows. Independent
blind scoring of a full set remains outstanding, and the report does not claim
otherwise.

**Alias coverage caps recall before any model runs.** Rule 3 needs both
variables named in the cited passage, through a hand-written alias table. Three
of the 46 ontology variables are never named in any of the 16,472 passages, and
five more appear in fewer than ten. We did not extend the table: it is an input
to rule 3, so changing it would alter the verifier for every condition at once
and leave every reported number describing a configuration that no longer
exists.

**The proposal's own worked example cannot be built from the corpus it froze.**
The chain runs crude → ATF price → airline costs → airline shares. Airline
costs appear in two passages and airline shares in none, and adjudication
separately dropped the crude-to-ATF link.

**Other limits.** One model family, one time window, English-language national
press only. The verifier may share the generator's blind spots, being the same
model. The candidates may have seen 2026 news in training. Retrieval relevance
judgements are automated, and the safety screen is a heuristic pass rather than
a certification. The challenge set's detections are ground truth, since each
corruption was applied mechanically to a known link, but its false-alarm rate
is only as good as the references behind the controls.

## 9. Conclusions

We built a system that measures, link by link, how far an explanation of
financial news is actually backed by its sources. The measuring worked. The
answer it gave is mixed, and the mixed part is the useful part.

**Checking links is worth doing and is not enough on its own.** We built 38
corrupted links that no fixed rule can catch, because reversing a link leaves
the same two variables in the same passage with the same quoted words. Fixed
rules caught none. The language-model checker caught 17 and wrongly flagged 2
of 23 clean links. It does real work that rules cannot do, and it still misses
more than half.

**The problem may start earlier than we were looking.** In the model pilot the
generator quoted the wrong passage in 17 of 20 cases. A checker cannot repair
an explanation whose evidence was mismatched before it arrived. On this reading
the low establishment rate is mostly an extraction failure, and the selection
rule that broke a 61.0% tie on latency chose the weaker extractor.

**Our main claim did not survive the held-out test.** On the four development
questions our system beat ordinary RAG on unsupported links. On the two
held-out questions, scored with fresh labels, it showed no improvement at all
and found 12.5 points fewer correct links. That breaks the H2d recall guard we
set in advance, which exists to catch a checker that improves its score by
deleting links rather than fixing them.

**What we cannot say.** With this many questions, and almost no evidence at
distant links, RQ1 is unanswered: whether grounding decays with distance
remains open, because the gate for a trend was never met on any condition. What
we can say is narrower and still worth having. We have a working instrument, a
frozen corpus and signed reference set that others can check, a measured result
about the division of labour between rules and a model, and one honest negative
result about our own method — produced by a guard we wrote before we ran
anything.

## 10. References

Asai et al. (2024). [Self-RAG](https://arxiv.org/abs/2310.11511). ICLR.

Chen et al. (2024). [BGE M3-Embedding](https://arxiv.org/abs/2402.03216).

Cormack, Clarke and Buettcher (2009). Reciprocal rank fusion. SIGIR.

Feinstein and Cicchetti (1990). High agreement but low kappa. *Journal of
Clinical Epidemiology* 43(6).

Mariko et al. (2020). [FinCausal 2020](https://aclanthology.org/2020.fnp-1.3/). FNP.

Prasad et al. (2023). [ReCEval](https://aclanthology.org/2023.emnlp-main.622/). EMNLP.

Qwen Team (2025). [Qwen3 technical report](https://arxiv.org/abs/2505.09388).

Tan et al. (2022). [The Causal News Corpus](https://aclanthology.org/2022.lrec-1.246/). LREC.

Wang et al. (2025). [CausalRAG](https://aclanthology.org/2025.findings-acl.1165/). ACL Findings.

Xie et al. (2025). [FIRE](https://aclanthology.org/2025.findings-naacl.158/). NAACL Findings.

Yu, Li and Wang (2019). [Detecting causal language use in science findings](https://aclanthology.org/D19-1473/). EMNLP-IJCNLP.
