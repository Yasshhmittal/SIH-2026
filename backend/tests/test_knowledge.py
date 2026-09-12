"""Retrieval tests.

The relevance floor is the part worth pinning. Before it existed, "catalyst
regeneration temperature profile" returned three confident hits from a piping
corpus that says nothing about catalysts — RRF always ranks *something*, and a
confident citation to an irrelevant passage is exactly the failure a grounded
system must not produce.

These run against a temporary store, so they neither need nor touch the demo
corpus. Dense-dependent behaviour is exercised with synthetic vectors rather
than by calling Ollama, so the suite stays fast and offline.
"""

from __future__ import annotations

import numpy as np
import pytest

from prahari.knowledge.chunker import Chunk, chunk_pages
from prahari.knowledge.readers import Page
from prahari.knowledge.store import KnowledgeStore, significant_terms, tokenize


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """A KnowledgeStore backed by a temp directory."""
    monkeypatch.setattr("prahari.knowledge.store.ORGS_DIR", tmp_path)
    return KnowledgeStore("testorg")


def _chunk(text: str, page: int = 1, section: str = "") -> Chunk:
    return Chunk(text=text, page=page, section=section)


# ------------------------------------------------------------ tokenizing ---

def test_identifiers_survive_tokenization():
    """'8-P-1204' and '6.4' must stay single terms.

    Splitting them is what makes keyword search fail on exactly the queries an
    engineer types.
    """
    tokens = tokenize("Circuit 8-P-1204 measured 6.4 mm at CML-03")
    assert "8-p-1204" in tokens
    assert "6.4" in tokens
    assert "cml-03" in tokens


def test_significant_terms_drops_noise():
    terms = significant_terms("What is the minimum thickness per the procedure")
    assert "minimum" in terms
    assert "thickness" in terms
    # stopwords and ubiquitous domain words carry no signal
    assert "the" not in terms
    assert "per" not in terms
    assert "procedure" not in terms


# ------------------------------------------------------------------ store ---

def test_add_and_stats(store):
    store.add_document(
        doc_id="d1", filename="SOP.txt", kind="text",
        chunks=[_chunk("retirement thickness shall be 6.4 mm")],
    )
    stats = store.stats()
    assert stats["documents"] == 1
    assert stats["chunks"] == 1
    assert stats["embedded_chunks"] == 0        # no vectors supplied


def test_bm25_finds_exact_identifier(store):
    store.add_document(
        doc_id="d1", filename="survey.txt", kind="text",
        chunks=[
            _chunk("Circuit 8-P-1204 overhead vapour line, nominal 8.0 mm"),
            _chunk("Circuit 6-P-0901 pumparound line, nominal 6.0 mm"),
        ],
    )
    hits = store.search("8-P-1204", k=5)
    assert len(hits) == 1
    assert "8-P-1204" in hits[0].text


def test_irrelevant_query_returns_nothing(store):
    """The regression this floor exists for."""
    store.add_document(
        doc_id="d1", filename="SOP-INS-07.txt", kind="text",
        chunks=[
            _chunk("The minimum retirement thickness for 8 inch carbon steel "
                   "piping in sour service shall be 6.4 mm."),
            _chunk("Re-inspection shall occur at one half of calculated "
                   "remaining life, or five years, whichever is the lesser."),
        ],
    )
    assert store.search("catalyst regeneration temperature profile", k=5) == []


def test_single_generic_term_is_not_enough(store):
    """A lone ubiquitous word must not keep an unrelated chunk alive."""
    store.add_document(
        doc_id="d1", filename="SOP-INS-11.txt", kind="text",
        chunks=[_chunk("Insulation shall be removed where the operating "
                       "temperature lies between -4 and 175 degrees Celsius.")],
    )
    # 'temperature' is shared but carries no signal here
    assert store.search("catalyst regeneration temperature", k=5) == []
    # a discriminating term does retrieve it
    assert len(store.search("insulation removal", k=5)) == 1


def test_dense_alone_can_carry_a_paraphrase(store):
    """A strong vector match with no shared vocabulary must still surface.

    This is the case hybrid search exists for, so the floor must not require
    term overlap when the dense signal is genuinely strong.
    """
    target = np.ones(8, dtype=np.float32)
    other = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=np.float32)

    store.add_document(
        doc_id="d1", filename="SOP.txt", kind="text",
        chunks=[_chunk("components below this value shall be withdrawn"),
                _chunk("unrelated administrative filing guidance")],
        embeddings=[target, other],
    )

    hits = store.search("wholly different wording", k=5, query_vector=target)
    assert len(hits) == 1
    assert "withdrawn" in hits[0].text
    assert hits[0].dense_rank == 1


def test_weak_dense_match_without_overlap_is_rejected(store):
    """Below the calibrated floor and with no shared term: drop it."""
    stored = np.array([1, 0, 0, 0], dtype=np.float32)
    # ~0.45 cosine — the noise band for bge-m3, below the 0.52 floor
    query = np.array([0.45, 0.893, 0, 0], dtype=np.float32)

    store.add_document(
        doc_id="d1", filename="SOP.txt", kind="text",
        chunks=[_chunk("administrative filing guidance")],
        embeddings=[stored],
    )
    assert store.search("zzz qqq", k=5, query_vector=query) == []


def test_org_isolation(tmp_path, monkeypatch):
    """One organisation must never retrieve another's chunks."""
    monkeypatch.setattr("prahari.knowledge.store.ORGS_DIR", tmp_path)

    mrpl = KnowledgeStore("mrpl")
    other = KnowledgeStore("defence_unit_a")

    mrpl.add_document(doc_id="m1", filename="mrpl_sop.txt", kind="text",
                      chunks=[_chunk("MRPL retirement thickness is 6.4 mm")])
    other.add_document(doc_id="d1", filename="other_sop.txt", kind="text",
                       chunks=[_chunk("Defence unit retirement thickness is 9.1 mm")])

    mrpl_hits = mrpl.search("retirement thickness", k=5)
    assert len(mrpl_hits) == 1
    assert "MRPL" in mrpl_hits[0].text

    other_hits = other.search("retirement thickness", k=5)
    assert len(other_hits) == 1
    assert "Defence" in other_hits[0].text


def test_delete_document_removes_postings(store):
    store.add_document(doc_id="d1", filename="a.txt", kind="text",
                       chunks=[_chunk("retirement thickness 6.4 mm")])
    assert store.search("retirement thickness", k=5)

    assert store.delete_document("d1") is True
    assert store.search("retirement thickness", k=5) == []
    assert store.stats()["chunks"] == 0


def test_reingest_replaces_rather_than_duplicates(store):
    for _ in range(3):
        store.add_document(doc_id="d1", filename="a.txt", kind="text",
                           chunks=[_chunk("retirement thickness 6.4 mm")])
    assert store.stats()["documents"] == 1
    assert store.stats()["chunks"] == 1


def test_empty_index_search_is_not_an_error(store):
    assert store.search("anything", k=5) == []


# ---------------------------------------------------------------- chunker ---

def test_table_rows_are_not_split():
    rows = "\n".join(f"CML-{i:02d} | Elbow E-{i} | 8.0 | {8.0 - i * 0.1:.1f} | 6.4"
                     for i in range(1, 40))
    page = Page(number=1, text=f"READINGS\n{rows}")

    chunks = chunk_pages([page], document="survey.txt")
    assert chunks
    for chunk in chunks:
        for line in chunk.text.splitlines():
            if "CML-" in line:
                # a surviving row keeps all five fields
                assert line.count("|") == 4, f"row was split: {line!r}"


def test_heading_is_carried_into_the_chunk():
    page = Page(number=1, text=(
        "4.2 Retirement thickness\n\n"
        "The minimum retirement thickness for 8 inch carbon steel piping in "
        "sour service shall be 6.4 mm.\n"
    ))
    chunks = chunk_pages([page], document="SOP.txt")
    assert len(chunks) == 1
    assert chunks[0].section.startswith("4.2")
    assert "6.4 mm" in chunks[0].text


def test_page_numbers_are_preserved_for_citation():
    pages = [Page(1, "First page about thickness criteria."),
             Page(2, "Second page about inspection intervals.")]
    chunks = chunk_pages(pages, document="SOP.txt")
    assert {c.page for c in chunks} == {1, 2}


def test_empty_pages_are_skipped():
    pages = [Page(1, ""), Page(2, "   "), Page(3, "Real content about piping.")]
    chunks = chunk_pages(pages, document="SOP.txt")
    assert len(chunks) == 1
    assert chunks[0].page == 3
