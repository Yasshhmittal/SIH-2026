"""Check that hybrid retrieval returns the right passages."""

from prahari.knowledge.search import search_knowledge
from prahari.knowledge.store import get_store

print("kb:", get_store("mrpl").stats())
print()

QUERIES = [
    # exact identifier — should be found by BM25 even if embeddings miss it
    "8-P-1204",
    # the governing number, phrased as an engineer would ask
    "minimum retirement thickness for 8 inch sour service piping",
    # paraphrase with none of the document's words — tests the dense side
    "how thin is too thin before we have to replace a pipe",
    # a different document entirely
    "when do I need management of change approval",
    # a number that appears in exactly one clause
    "0.25 mm per year",
    # should find nothing — checks we do not invent hits
    "catalyst regeneration temperature profile",
]

for query in QUERIES:
    observation = search_knowledge(query, org_id="mrpl", k=3)
    print(f"Q: {query}")
    print(f"   {observation.summary}")
    for chunk in observation.data.get("chunks", []):
        snippet = " ".join(chunk["text"].split())[:110]
        ranks = f"dense={chunk['dense_rank']} sparse={chunk['sparse_rank']}"
        print(f"   [{chunk['id']}] {chunk['document']} p.{chunk['page']} "
              f"score={chunk['score']} {ranks}")
        print(f"        {snippet}...")
    print()
