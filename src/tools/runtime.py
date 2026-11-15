"""Six read-only tools with trusted corpus identity, cutoff and budget enforcement."""

from __future__ import annotations

import time

from retrieval.filters import checked_hits
from schema import (
    MAX_TOOL_CALLS,
    CandidateEvidence,
    Edge,
    Provenance,
    ToolName,
    VerifyVerdict,
    parse_tool_call,
)
from schema.tools import (
    CounterSearchResult,
    GetSeriesResult,
    SearchCorpusResult,
    StopResult,
    ToolError,
    UpdateGraphResult,
    VerifyEdgeResult,
)
from verify.paths import rebuild

RESULTS = {
    ToolName.SEARCH_CORPUS: SearchCorpusResult,
    ToolName.GET_SERIES: GetSeriesResult,
    ToolName.VERIFY_EDGE: VerifyEdgeResult,
    ToolName.COUNTER_SEARCH: CounterSearchResult,
    ToolName.UPDATE_GRAPH: UpdateGraphResult,
    ToolName.STOP: StopResult,
}


class ToolRuntime:
    def __init__(
        self,
        *,
        graph,
        retriever,
        series,
        verifier=None,
        logger=None,
        require_verification=True,
        budget=MAX_TOOL_CALLS,
    ):
        if not 1 <= budget <= MAX_TOOL_CALLS:
            raise ValueError("tool budget must be between 1 and 12")
        self.graph, self.retriever, self.series = graph, retriever, series
        self.verifier, self.logger, self.require_verification = (
            verifier,
            logger,
            require_verification,
        )
        self.budget, self.calls_used, self.graph_version = budget, 0, 0
        self.corpus = {p.passage_id: p for p in retriever.passages}
        self.seen: set[str] = set()
        self.approved: dict[str, Edge] = {}
        self.spans: dict[tuple[str, str], str] = {}
        self.call_ids: set[str] = set()
        self.searches_done = self.empty_searches = 0
        self.stopped = False
        self.extra_nodes = {}

    @property
    def remaining(self):
        return self.budget - self.calls_used

    @property
    def open_edges(self):
        return [e.edge_id for e in self.graph.edges if not e.is_asserted and e.verdict is None]

    def set_edges(self, edges):
        self.graph = rebuild(
            query_id=self.graph.query_id,
            anchor=self.graph.anchor,
            as_of=self.graph.as_of,
            edges=edges,
            condition=self.graph.condition,
        )
        if self.extra_nodes:
            existing = {node.var for node in self.graph.nodes}
            self.graph = type(self.graph).model_validate(
                {
                    **self.graph.model_dump(),
                    "nodes": [
                        *self.graph.nodes,
                        *(node for var, node in self.extra_nodes.items() if var not in existing),
                    ],
                }
            )
        self.graph_version += 1

    def call(self, tool: str, **args):
        return self.dispatch(
            {
                "tool": tool,
                "call_id": f"call-{self.calls_used+1}",
                "step": self.calls_used,
                "args": args,
            }
        )

    def dispatch(self, payload):
        call = parse_tool_call(payload.model_dump() if hasattr(payload, "model_dump") else payload)
        result_class = RESULTS[call.tool]
        if self.stopped or self.remaining <= 0:
            return result_class(
                call_id=call.call_id,
                ok=False,
                error=ToolError(
                    kind="budget_exhausted", message="run ended or tool budget exhausted"
                ),
            )
        if call.call_id in self.call_ids:
            raise ValueError("tool call ids cannot be reused")
        self.call_ids.add(call.call_id)
        self.calls_used += 1
        if self.logger:
            self.logger.step = self.calls_used
            self.logger.write("tool_call", call=call, budget_remaining=self.remaining)
        started, new_count = time.monotonic(), 0
        try:
            if hasattr(call.args, "as_of") and call.args.as_of != self.graph.as_of:
                result = result_class(
                    call_id=call.call_id,
                    ok=False,
                    error=ToolError(
                        kind="after_as_of", message="tool cutoff must equal the pinned query cutoff"
                    ),
                )
            else:
                result = self._execute(call)
            if isinstance(result, (SearchCorpusResult, CounterSearchResult)) and result.ok:
                ids = {p.passage_id for p in result.passages}
                new_count = len(ids - self.seen)
                self.seen.update(ids)
                self.searches_done += 1
                self.empty_searches = self.empty_searches + 1 if new_count == 0 else 0
        except (ValueError, KeyError, OSError, RuntimeError) as exc:
            result = result_class(
                call_id=call.call_id,
                ok=False,
                error=ToolError(kind="backend_error", message=str(exc)),
            )
        result.latency_ms = (time.monotonic() - started) * 1000
        if self.logger:
            self.logger.write("tool_result", result=result, new_passages=new_count)
            self.logger.write(
                "state",
                open_edges=self.open_edges,
                verified_edges=[
                    e.edge_id for e in self.graph.edges if e.verified_by == "rules+llm"
                ],
                searches_done=self.searches_done,
                budget_remaining=self.remaining,
            )
        return result

    def _execute(self, call):
        args, cid = call.args, call.call_id
        if call.tool == ToolName.SEARCH_CORPUS:
            hits = checked_hits(
                self.retriever.search(**args.model_dump()),
                self.corpus,
                args,
                self.retriever.aliases,
            )
            return SearchCorpusResult(
                call_id=cid,
                passages=[h.passage for h in hits[: args.k]],
                scores=[h.score for h in hits[: args.k]],
            )
        if call.tool == ToolName.GET_SERIES:
            return self.series.get_series(args, call_id=cid)
        if call.tool == ToolName.COUNTER_SEARCH:
            from schema.tools import SearchCorpusArgs

            query = f"{args.dst_var.replace('_', ' ')} {args.direction} causes reasons drivers"
            search_args = SearchCorpusArgs(
                query=query, as_of=args.as_of, k=args.k, must_mention=[args.dst_var]
            )
            hits = checked_hits(
                self.retriever.search(**search_args.model_dump()),
                self.corpus,
                search_args,
                self.retriever.aliases,
            )
            passages = [hit.passage for hit in hits[: args.k]]
            excluded = {args.dst_var, *args.exclude_src_vars}
            competing = sorted(
                {
                    var
                    for p in passages
                    for var in self.retriever.aliases.mapping
                    if var not in excluded and self.retriever.aliases.mentions(p.text, var)
                }
            )
            return CounterSearchResult(call_id=cid, passages=passages, competing_src_vars=competing)
        if call.tool == ToolName.VERIFY_EDGE:
            edge = next((e for e in self.graph.edges if e.edge_id == args.edge_id), None)
            if edge is None:
                return VerifyEdgeResult(
                    call_id=cid,
                    ok=False,
                    error=ToolError(kind="unknown_edge", message=args.edge_id),
                )
            if self.verifier is None:
                raise ValueError("verifier is not configured")
            # A later verification attempt replaces approval, including a rejection.
            self.approved.pop(edge.edge_id, None)

            result = VerifyEdgeResult(
                call_id=cid,
                edge_id=edge.edge_id,
                verdict=VerifyVerdict.UNSUPPORTED,
                provenance=Provenance.MODEL_INFERRED,
            )
            candidates = list(edge.candidate_evidence)

            for pid in args.passage_ids:
                if pid not in self.seen or pid not in self.corpus:
                    continue

                passage = self.corpus[pid]
                span = self.spans.get((edge.edge_id, pid), passage.text)

                result = self.verifier.verify(
                    edge,
                    passage=passage,
                    span=span,
                    as_of=self.graph.as_of,
                    call_id=cid,
                )

                if result.provenance == Provenance.SOURCE_ASSERTED:
                    self.approved[edge.edge_id] = Edge.model_validate(
                        {
                            **edge.model_dump(),
                            "provenance": result.provenance,
                            "strength": result.strength,
                            "evidence_span": result.evidence_span,
                            "evidence_doc_id": passage.doc_id,
                            "evidence_passage_id": passage.passage_id,
                            "evidence_published_at": passage.published_at,
                            "candidate_evidence": candidates,
                            "verified_by": "rules+llm",
                            "verdict": result.verdict,
                        }
                    )
                    break

                if result.verdict is not None:
                    candidate = CandidateEvidence(
                        passage_id=passage.passage_id,
                        doc_id=passage.doc_id,
                        span=span,
                        verdict=result.verdict,
                        reason=", ".join(result.rule_failures) or None,
                    )

                    key = (candidate.passage_id, candidate.span, candidate.verdict)
                    existing = {(c.passage_id, c.span, c.verdict) for c in candidates}

                    if key not in existing:
                        candidates.append(candidate)

            if candidates != list(edge.candidate_evidence):
                updated = Edge.model_validate(
                    {
                        **edge.model_dump(),
                        "candidate_evidence": candidates,
                    }
                )
                edges = [updated if e.edge_id == edge.edge_id else e for e in self.graph.edges]
                self.set_edges(edges)

            return result
        if call.tool == ToolName.UPDATE_GRAPH:
            edges = list(self.graph.edges)
            if args.op == "add_node":
                if args.node.is_anchor or any(
                    node.var == args.node.var for node in self.graph.nodes
                ):
                    raise ValueError("cannot add another anchor or a duplicate node")
                self.extra_nodes[args.node.var] = args.node
                self.set_edges(edges)
                return UpdateGraphResult(
                    call_id=cid, applied=True, graph_version=self.graph_version
                )
            if args.op == "add_edge":
                edge = Edge.model_validate(args.edge.model_dump())
                if any(e.edge_id == edge.edge_id for e in edges):
                    raise ValueError("duplicate graph edge id")
                if edge.is_asserted and self.require_verification:
                    raise ValueError("new asserted edges require semantic verification")
                self._check_citation(edge)
                edges.append(edge)
            else:
                index = next(
                    (i for i, edge in enumerate(edges) if edge.edge_id == args.edge_id), None
                )
                if index is None:
                    return UpdateGraphResult(
                        call_id=cid,
                        ok=False,
                        error=ToolError(kind="unknown_edge", message=args.edge_id),
                    )
                if args.op == "drop_edge":
                    edges.pop(index)
                    self.approved.pop(args.edge_id, None)
                elif self.require_verification and (
                    args.provenance == Provenance.SOURCE_ASSERTED
                    or (args.provenance is None and edges[index].is_asserted)
                ):
                    proof = self.approved.get(args.edge_id)
                    current = edges[index]
                    if proof is None or (proof.src_var, proof.dst_var, proof.direction) != (
                        current.src_var,
                        current.dst_var,
                        current.direction,
                    ):
                        raise ValueError("asserted relabel has no matching verification result")
                    if args.strength is not None and args.strength != proof.strength:
                        raise ValueError("relabel cannot overrule verifier strength")
                    if args.edge is not None and args.edge != proof:
                        raise ValueError("relabel cannot replace verifier-approved evidence")
                    edges[index] = proof
                else:
                    data = edges[index].model_dump()
                    if args.edge is not None and not self.require_verification:
                        replacement = Edge.model_validate(args.edge.model_dump())
                        if (
                            replacement.edge_id,
                            replacement.src_var,
                            replacement.dst_var,
                            replacement.direction,
                        ) != (
                            edges[index].edge_id,
                            edges[index].src_var,
                            edges[index].dst_var,
                            edges[index].direction,
                        ):
                            raise ValueError("relabel must preserve edge identity and relation")
                        self._check_citation(replacement)
                        data = replacement.model_dump()
                    if args.strength is not None:
                        data["strength"] = args.strength
                    if args.provenance is not None:
                        data["provenance"] = args.provenance
                    if data["provenance"] == Provenance.MODEL_INFERRED:
                        data.update(
                            evidence_span=None,
                            evidence_doc_id=None,
                            evidence_passage_id=None,
                            evidence_published_at=None,
                            verdict=VerifyVerdict.UNSUPPORTED,
                            verified_by=None,
                        )
                        self.approved.pop(args.edge_id, None)
                    edges[index] = Edge.model_validate(data)
            self.set_edges(edges)
            return UpdateGraphResult(call_id=cid, applied=True, graph_version=self.graph_version)
        if call.tool == ToolName.STOP:
            if args.reason == "two_searches_added_nothing" and self.empty_searches < 2:
                raise ValueError("two unchanged searches have not occurred")
            if args.reason == "important_edges_resolved" and self.open_edges:
                raise ValueError("unresolved graph edges remain")
            if args.reason == "budget_exhausted" and self.remaining > 0:
                raise ValueError("tool budget remains")
            self.stopped = True
            return StopResult(
                call_id=cid, calls_used=self.calls_used, open_edges_remaining=len(self.open_edges)
            )
        raise ValueError("unknown tool")

    def _check_citation(self, edge):
        if not edge.is_asserted:
            return
        passage = self.corpus.get(edge.evidence_passage_id)
        if (
            passage is None
            or not passage.visible_at(self.graph.as_of)
            or (
                edge.evidence_doc_id != passage.doc_id
                or edge.evidence_published_at != passage.published_at
            )
        ):
            raise ValueError("asserted citation must match a date-visible trusted corpus passage")
