"""Clean Inline-XBRL 10-K HTML -> ~400-word chunks (80 overlap) -> local embeddings -> ChromaDB."""
import logging
import re
import time

from bs4 import BeautifulSoup

from finsight.config import (CHROMA_DIR, CHUNK_OVERLAP, CHUNK_WORDS, COLLECTION,
                             EMBED_MODEL, FILINGS_DIR)

log = logging.getLogger(__name__)


def clean_html(html: str) -> str:
    """Keep only human-readable prose (strip machine-readable XBRL metadata)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["ix:header", "script", "style"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        if not getattr(tag, "decomposed", False):
            tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def chunk_words(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if chunks and len(piece) < overlap:  # tail already contained in previous chunk
            break
        chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks


def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def build_index(tickers: list[str] | None = None, batch: int = 64) -> int:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)
    col = get_collection()
    files = sorted(FILINGS_DIR.glob("*_10K.html"))
    total = 0
    for f in files:
        tk = f.name.split("_")[0]
        if tickers and tk not in tickers:
            continue
        chunks = chunk_words(clean_html(f.read_text(encoding="utf-8", errors="ignore")))
        existing = set(col.get(where={"ticker": tk}, include=[])["ids"])  # resumable
        todo = [(i, c) for i, c in enumerate(chunks) if f"{tk}-10K-{i}" not in existing]
        for s in range(0, len(todo), batch):
            part = todo[s:s + batch]
            for attempt in range(3):  # retry: protects against transient Chroma/AV file locks
                try:
                    emb = model.encode([c for _, c in part], normalize_embeddings=True).tolist()
                    col.upsert(
                        ids=[f"{tk}-10K-{i}" for i, _ in part],
                        documents=[c for _, c in part],
                        embeddings=emb,
                        metadatas=[{"ticker": tk, "filing_type": "10-K", "chunk_index": i} for i, _ in part],
                    )
                    break
                except Exception as e:
                    log.warning("%s batch retry %d: %s", tk, attempt + 1, e)
                    time.sleep(2)
            else:
                raise RuntimeError(f"embedding failed for {tk}")
        total += len(todo)
        log.info("%s: %d chunks (%d new)", tk, len(chunks), len(todo))
    return total
