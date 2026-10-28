"""Replay recorded Codex source judgments on the 43 existing development seeds.

This is a source-evidence audit, not independent human annotation. It never
writes a human receipt, changes the blinded packet, or certifies pool recall.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from retrieval.review import read_queries

# Judgments were made from each complete source paragraph and the fixed question.
# Keys are question number and passage ordinal within its original seed document.
DECISIONS = {
    (1, 3): (
        "relevant",
        "rising oil prices, thus weighing on the local currency.",
        "Explicitly connects India's fiscal/current-account deficit risk from oil to its currency.",
    ),
    (2, 6): (
        "relevant",
        "shipping companies impose war risk premiums and reroute vessels along longer, safer paths",
        "Names the freight-cost mechanisms requested.",
    ),
    (2, 7): (
        "irrelevant",
        None,
        "Lists freight prices without explaining why charges rose; the adjacent paragraph is not part of this passage.",
    ),
    (3, 8): (
        "relevant",
        "Corresponding inflation rates for rural and urban are 3.37% and 3.02%, respectively.",
        "The same paragraph states provisional national 3.21% and both requested sector rates for February.",
    ),
    (4, 1): (
        "irrelevant",
        None,
        "Documents the yield rise despite cuts but supplies no driver for the question's why.",
    ),
    (4, 2): (
        "relevant",
        "largely due to oversupply of bonds and heightened geopolitical risks.",
        "Explicitly explains the divergence of yields from policy cuts.",
    ),
    (5, 0): (
        "relevant",
        "supportive dollar flows for the currency, spurred by banks\u2019 unwinding of arbitrage positions, dissipated.",
        "States both oil above $100 and disappearance of supportive dollar flows in the specified decline.",
    ),
    (5, 2): (
        "uncertain",
        None,
        "Reports unwinding and breathing room; the measures and their relation to the current decline require omitted context.",
    ),
    (6, 4): (
        "irrelevant",
        None,
        "Earlier policy history and the December Goldilocks assessment do not state the April growth/inflation outlook.",
    ),
    (6, 5): (
        "uncertain",
        None,
        "That assessment is an unresolved reference in this isolated paragraph; the changed outlook is not stated.",
    ),
    (6, 7): (
        "relevant",
        "CPI inflation is projected at 4.6%",
        "States the new FY27 inflation forecast; one part of the requested outlook.",
    ),
    (6, 8): (
        "relevant",
        "pencilled in a slower 6.9% expansion for FY27",
        "States the slower FY27 growth forecast; one part of the requested outlook.",
    ),
    (7, 3): (
        "relevant",
        "higher prices for aluminium, chemicals, electrical components, fuel, leather, petroleum products and rubber.",
        "Connects the April cost burden to conflict and identified inputs.",
    ),
    (7, 4): (
        "irrelevant",
        None,
        "States how fast costs rose, not the drivers requested in the question.",
    ),
    (8, 0): (
        "relevant",
        "amid elevated Aviation Turbine Fuel (ATF) prices.",
        "Connects Air India's international suspensions/reductions to fuel costs.",
    ),
    (8, 2): (
        "relevant",
        "prolonged airspace restrictions along with geopolitical disruptions have impacted the airline\u2019s international operations.",
        "Names both the fuel and airspace pressures.",
    ),
    (9, 5): (
        "relevant",
        "the pressure stemming simultaneously from rupee depreciation and raw material inflation.",
        "Explains inability to pass through the combined cost burden.",
    ),
    (9, 6): (
        "relevant",
        "the hedging is done more prudently and for a longer-term horizon.",
        "Direct quote explains longer hedges in response to rupee pressure.",
    ),
    (10, 3): (
        "relevant",
        "with the RBI bearing hedging costs, and banks can offer better returns to overseas depositors.",
        "Explains how FCNR(B) measures were expected to mobilise foreign capital.",
    ),
    (10, 4): (
        "relevant",
        "providing a meaningful buffer to the rupee while easing broader funding pressures",
        "Identifies the expected currency/funding benefit; preserves the forecast as an expectation.",
    ),
    (11, 4): (
        "relevant",
        "Poor rainfall can also fuel food inflation",
        "Directly connects deficient rainfall to food inflation and gives perishable examples.",
    ),
    (12, 7): (
        "relevant",
        "Retail inflation based on Consumer Price Index in May, 2026 is 3.93%",
        "Correct May headline release value.",
    ),
    (12, 8): (
        "relevant",
        "Year on year food inflation, based on Consumer Food Price Index, in May, 2026 is 4.78%",
        "Correct May food release value.",
    ),
    (13, 1): (
        "relevant",
        "Saudi Arabia cut its August crude oil prices for Asian buyers amid easing geopolitical tensions in West Asia",
        "The paragraph explicitly links this price news to rupee strength and short covering.",
    ),
    (13, 4): (
        "relevant",
        "Resumption of foreign portfolio investor (FPI) flows into Indian equities also helped stabilise the rupee.",
        "Directly states the portfolio-flow contribution.",
    ),
    (14, 1): (
        "relevant",
        "consumer inflation averaged 3.9% in April-June, compared with the RBI's forecast of 4.2%.",
        "Explicitly says ANZ and Citi withdrew the August hike forecast after this downside inflation surprise.",
    ),
    (14, 2): (
        "relevant",
        "the central bank prioritises growth over inflation management.",
        "Gives a reported policy-priority reason for the hold expectations and forecast withdrawal.",
    ),
    (15, 4): (
        "relevant",
        "pushed the rupee to a record low in May, depressing returns for foreign currency holders.",
        "Links oil costs and selling to rupee depreciation and foreign-currency returns.",
    ),
    (15, 5): (
        "relevant",
        "Overseas investors cited stretched valuations alongside FX and oil risks for reallocating capital elsewhere.",
        "Explicitly states why foreign investors reallocated.",
    ),
    (16, 3): (
        "relevant",
        "He also flagged risks from fresh Trump tariffs.",
        "A direct partial answer about the governor's trade-risk warning.",
    ),
    (16, 5): (
        "relevant",
        "disrupting key trade routes and supply chains, amplifying market volatility and denting business sentiment.",
        "Direct statement of the supply-chain/trade-route warning.",
    ),
    (16, 6): (
        "relevant",
        "Trade uncertainty lingered as the US imposed fresh tariffs",
        "Direct statement of the new tariff and global outlook risk.",
    ),
    (17, 1): (
        "relevant",
        "supported by the depreciation of the Indian rupee and higher prices amid supply disruptions.",
        "Directly explains exporters' April-June revenue growth.",
    ),
    (17, 2): (
        "relevant",
        "INR depreciation along with high prices owing to supply shock have supported the top line.",
        "Direct quoted revenue mechanism; later fading remains a forecast.",
    ),
    (17, 3): (
        "relevant",
        "Nuvama attributed the acceleration mainly to prices and depreciation of the rupee.",
        "Names the drivers of the stated first-quarter revenue acceleration.",
    ),
    (18, 6): (
        "relevant",
        "Retail inflation based on Consumer Price Index in July, 2026 is 4.45%",
        "Correct July headline release value.",
    ),
    (18, 7): (
        "relevant",
        "Year on year food inflation, based on Consumer Food Price Index, in July, 2026 is 5.52%",
        "Correct July food release value.",
    ),
    (19, 0): (
        "relevant",
        "expensive imported LNG and weak fuel marketing margins squeeze downstream profitability",
        "Explicitly links energy input costs and downstream margins.",
    ),
    (19, 3): (
        "relevant",
        "the benefit is being increasingly offset by higher crude costs and marketing losses.",
        "Explains the offset to strong refining spreads.",
    ),
    (19, 5): (
        "relevant",
        "higher LNG prices beginning to affect the cost structure of gas-consuming businesses.",
        "States the LNG cost pressure and expected effect; not a causal estimate.",
    ),
    (20, 1): (
        "relevant",
        "selling dollars through government-owned banks to prevent further weakening of the rupee beyond the 96 level.",
        "States the contemporaneous RBI intervention reported by traders.",
    ),
    (20, 2): (
        "relevant",
        "the local currency continued to be under pressure amid a surge in global bond yields.",
        "States yield pressure and the reported inflation/Fed-hike expectations.",
    ),
    (20, 3): (
        "relevant",
        "A rebound in crude oil prices, elevated bond yields and rising expectations of higher interest rates",
        "Directly names the three reported currency headwinds.",
    ),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(*, pairs: Path, packet: Path, corpus: Path, output: Path, report: Path):
    if output.exists() or report.exists():
        raise ValueError("choose new audit/pair paths; retain existing judgments")
    data = json.loads(packet.read_text())
    assert sha256(corpus) == data["corpus_sha256"]
    assert sha256(pairs) == data["pairs_sha256"]
    by_id = {c["passage"]["passage_id"]: c["passage"] for c in data["candidates"]}
    rows, new_pairs, seen = [], [], set()
    for q in read_queries(pairs):
        positives = []
        for pid in sorted(q.relevant_passage_ids):
            p = by_id[pid]
            key = (int(q.query_id.rsplit("-", 1)[1]), int(pid.rsplit("#p", 1)[1]))
            assert key not in seen and key in DECISIONS
            seen.add(key)
            decision, span, note = DECISIONS[key]
            assert p["published_at"][:10] <= str(q.as_of)
            if decision == "relevant":
                assert span and span in p["text"], f"nonverbatim quote: {key}"
                positives.append(pid)
            else:
                assert span is None
            rows.append(
                {
                    "query_id": q.query_id,
                    "passage_id": pid,
                    "decision": decision,
                    "evidence_span": span,
                    "reason": note,
                    "source_text_sha256": hashlib.sha256(p["text"].encode()).hexdigest(),
                    "source_url": p["url"],
                }
            )
        assert positives, f"no audited seed for {q.query_id}"
        new_pairs.append(q.model_copy(update={"relevant_passage_ids": frozenset(positives)}))
    assert seen == set(DECISIONS)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(
                {
                    **q.model_dump(mode="json"),
                    "relevant_passage_ids": sorted(q.relevant_passage_ids),
                },
                sort_keys=True,
            )
            + "\n"
            for q in new_pairs
        )
    )
    result = {
        "method": "Codex source-evidence audit of existing development seeds; not independent human annotation",
        "reviewed_on": "2026-10-25",
        "independent_human_review": False,
        "blinded_to_previous_results": False,
        "research_acceptance": False,
        "scope": "43 pre-existing positive seeds only; no exhaustive candidate-pool judgment or corpus recall claim",
        "criterion": "The isolated paragraph must directly answer at least part of the fixed question. A driver question requires a driver, not only the outcome. Unresolved references remain uncertain.",
        "input_pairs_sha256": sha256(pairs),
        "packet_sha256": sha256(packet),
        "corpus_sha256": sha256(corpus),
        "audited_pairs_sha256": sha256(output),
        "audit_source_sha256": sha256(Path(__file__)),
        "queries": len(new_pairs),
        "decisions": dict(Counter(r["decision"] for r in rows)),
        "records": rows,
    }
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pairs", type=Path, default=Path("reports/retriever_temporal_v3_pairs.jsonl")
    )
    parser.add_argument(
        "--packet", type=Path, default=Path("data/interim/retrieval_review_temporal_v4/packet.json")
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    audit(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
