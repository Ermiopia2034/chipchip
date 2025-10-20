import os
import pytest


def test_rag_service_import():
    # Smoke test import, skip if optional dependency not installed locally
    try:
        from app.services.rag_service import VectorDBService  # noqa: F401
    except ModuleNotFoundError as e:
        if "chromadb" in str(e):
            pytest.skip("chromadb not installed in local test env")
        raise


def test_rag_semantic_search():
    # Run only if GEMINI_API_KEY present; otherwise skip
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY not set")

    from app.services.rag_service import VectorDBService

    s = VectorDBService()
    try:
        r = s.semantic_search("storage", n_results=1)
    except Exception as e:
        # If collection uninitialized, ingest and retry
        kb_path = "/data/product_knowledge_base.csv"
        if os.path.isfile(kb_path):
            s.ingest_knowledge_base(kb_path)
            r = s.semantic_search("storage", n_results=1)
        else:
            pytest.skip("KB CSV not available inside container")

    assert isinstance(r, dict)
    assert "documents" in r
    docs = r.get("documents") or []
    # chroma returns list-of-lists for documents
    if isinstance(docs, list) and docs and isinstance(docs[0], list):
        docs = docs[0]
    assert len(docs) >= 1
