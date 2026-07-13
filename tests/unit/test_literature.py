from acero.evaluation.retrieval_metrics import evaluate
from acero.literature.citations import CitationVerifier, find_duplicate_documents
from acero.literature.documents import chunk_text, ingest_document
from acero.literature.retrieval import BM25Index


def test_chunking_nonempty_and_overlapping():
    text = "Sentence one. " * 200
    chunks = chunk_text(text, target_chars=200, overlap=40)
    assert len(chunks) > 1
    assert all(c[2] for c in chunks)


def test_ingest_local_document(corpus_dir):
    doc, frags = ingest_document(corpus_dir / "cooling.md", "proj_x", license="CC-BY")
    assert doc.checksum.startswith("sha256:")
    assert doc.license == "CC-BY"
    assert len(frags) >= 1
    for f in frags:
        assert f.document_id == doc.id
        assert f.hash.startswith("sha256:")


def test_retrieval_returns_provenance(corpus_dir):
    doc, frags = ingest_document(corpus_dir / "cooling.md", "proj_x")
    idx = BM25Index()
    idx.add_many(frags)
    hits = idx.search("exponential decay cooling constant", top_k=3)
    assert hits
    top = hits[0]
    assert top.provenance["document_id"] == doc.id
    assert "char_span" in top.provenance
    assert top.score > 0


def test_retrieval_ranks_relevant_doc_first(corpus_dir):
    d1, f1 = ingest_document(corpus_dir / "cooling.md", "p")
    d2, f2 = ingest_document(corpus_dir / "harmonic.md", "p")
    idx = BM25Index()
    idx.add_many(f1 + f2)
    hits = idx.search("pendulum oscillation period amplitude", top_k=3)
    assert hits[0].fragment.document_id == d2.id


def test_citation_verifier_rejects_fabricated(corpus_dir):
    doc, frags = ingest_document(corpus_dir / "cooling.md", "p")
    v = CitationVerifier([doc], frags)
    assert v.verify(doc.id, frags[0].id).ok
    assert not v.verify("doc_fake").ok
    assert not v.verify(doc.id, "frag_fake").ok


def test_duplicate_detection(corpus_dir):
    d1, _ = ingest_document(corpus_dir / "cooling.md", "p")
    d2, _ = ingest_document(corpus_dir / "cooling.md", "p")  # same bytes -> same checksum
    dups = find_duplicate_documents([d1, d2])
    assert dups and dups[0][0] == d1.id and dups[0][1] == d2.id


def test_store_roundtrip_and_index(lit_store, corpus_dir):
    doc, frags = ingest_document(corpus_dir / "cooling.md", "proj_store")
    lit_store.add(doc, frags)
    assert len(lit_store.documents("proj_store")) == 1
    idx = lit_store.build_index("proj_store")
    assert idx.size == len(frags)


def test_retrieval_metrics():
    preds = [["a", "b", "c"], ["x", "y", "z"]]
    rel = [{"b"}, {"q"}]
    m = evaluate(preds, rel, k=3)
    assert m.recall_at_k == 0.5   # query 1 hits, query 2 misses
    assert 0 < m.mrr <= 0.5
