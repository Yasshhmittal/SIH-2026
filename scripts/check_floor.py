"""Why does an irrelevant query still return hits? Inspect the raw signals."""

from prahari.knowledge.embed import embed_query
from prahari.knowledge.store import get_store, tokenize

store = get_store("mrpl")
QUERY = "catalyst regeneration temperature profile"

query_terms = set(tokenize(QUERY))
print(f"query terms: {sorted(query_terms)}")
print()

vector = embed_query(QUERY)
with store._connect() as conn:
    dense = store._dense(conn, vector, 10)
    sparse = store._bm25(conn, QUERY, 10)

    print("dense similarities (cosine):")
    for cid, sim in dense[:6]:
        row = conn.execute(
            "SELECT c.text, d.filename FROM chunks c "
            "JOIN documents d ON d.doc_id=c.doc_id WHERE chunk_id=?", (cid,)
        ).fetchone()
        overlap = query_terms & set(tokenize(row["text"]))
        print(f"  chunk {cid:>3}  sim={sim:.4f}  overlap={sorted(overlap) or 'NONE'}"
              f"  {row['filename'][:40]}")

    print()
    print("bm25 hits:")
    for cid, score in sparse[:6]:
        row = conn.execute(
            "SELECT c.text, d.filename FROM chunks c "
            "JOIN documents d ON d.doc_id=c.doc_id WHERE chunk_id=?", (cid,)
        ).fetchone()
        overlap = query_terms & set(tokenize(row["text"]))
        print(f"  chunk {cid:>3}  bm25={score:.4f}  overlap={sorted(overlap) or 'NONE'}"
              f"  {row['filename'][:40]}")

print()
print("--- for comparison, a genuinely relevant query ---")
good = "minimum retirement thickness 8 inch sour service"
good_terms = set(tokenize(good))
gv = embed_query(good)
with store._connect() as conn:
    for cid, sim in store._dense(conn, gv, 4):
        row = conn.execute("SELECT text FROM chunks WHERE chunk_id=?", (cid,)).fetchone()
        overlap = good_terms & set(tokenize(row["text"]))
        print(f"  chunk {cid:>3}  sim={sim:.4f}  overlap={sorted(overlap)}")
