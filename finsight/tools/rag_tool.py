"""RAG tool: semantic search over 10-K chunks (ChromaDB + local sentence-transformers)."""
from functools import lru_cache

from finsight.config import EMBED_MODEL


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def _collection():
    from finsight.ingestion.embed import get_collection
    return get_collection()


def search_filings(query: str, ticker: str | None = None, k: int = 5) -> dict:
    """Semantic search in 10-K filings. Optionally restrict to one ticker."""
    k = max(1, min(int(k), 8))
    where = {"ticker": ticker.strip().upper()} if ticker else None
    emb = _model().encode([query], normalize_embeddings=True).tolist()
    res = _collection().query(query_embeddings=emb, n_results=k, where=where)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"ticker": meta["ticker"], "chunk_index": meta["chunk_index"],
                     "filing": meta["filing_type"], "score": round(1 - dist, 3), "text": doc[:1500]})
    return {"query": query, "results": hits} if hits else {"query": query, "results": [],
                                                           "note": "No passages found (is the filing indexed?)"}
