"""Lexical BM25 retrieval over the whole corpus — the lexical half of hybrid retrieval.

The dense layer matches by meaning but misses exact and rare terms, and it indexes only items,
creatures and lore — so a quest searched for by a word in its own description was unreachable, because
quests matched by location name alone. BM25 ranks every corpus entry by term overlap over its full
text (name, aliases and description), so those lexical hits surface as candidates and the
cross-encoder reranker prunes them for precision. A thin wrapper over rank_bm25, and graceful: when
the library is absent, retrieval simply runs without the lexical pass.
"""


class Bm25:
    def __init__(self, doc_tokens, metas):
        from rank_bm25 import BM25Okapi
        self._bm = BM25Okapi(doc_tokens)
        self.metas = metas  # parallel list of {kind, name, fact, region}

    def top(self, query_tokens, n=15, min_score=1.0):
        """Top-n metas whose BM25 score clears min_score, best first."""
        if not query_tokens:
            return []
        scores = self._bm.get_scores(query_tokens)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
        return [(self.metas[i], float(scores[i])) for i in order if scores[i] >= min_score]


def available() -> bool:
    try:
        import rank_bm25  # noqa: F401
        return True
    except ImportError:
        return False
