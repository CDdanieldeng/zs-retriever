"""Tests for retrieval - search flow with mock providers."""
from app.services.providers.embedding_stub import StubEmbeddingProvider
from app.services.providers.rerank_stub import StubRerankProvider
from app.services.providers.vector_store_default import DefaultVectorStoreAdapter


def test_embedding_stub():
    provider = StubEmbeddingProvider()
    vecs = provider.embed(["hello", "world"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384
    assert provider.embed(["same"])[0] == provider.embed(["same"])[0]


def test_rerank_stub():
    provider = StubRerankProvider()
    results = provider.rerank("query", ["a", "b", "c"], top_n=2)
    assert len(results) == 2
    assert results[0].text == "a"
    assert results[0].score > results[1].score


def test_vector_store_upsert_search():
    from app.services.providers.base import VectorRecord

    vs = DefaultVectorStoreAdapter()
    embedder = StubEmbeddingProvider()
    vec = embedder.embed(["test text"])[0]
    vs.upsert([
        VectorRecord(
            chunk_id="c1",
            vector=vec,
            project_id="p1",
            file_id="f1",
            parent_id="par1",
            chunk_type="text",
            chunk_text="test text",
            loc={},
            index_version="v1",
            doc_hash="h1",
        )
    ])
    hits = vs.search(vec, top_k=5, project_id="p1", index_version="v1")
    assert len(hits) >= 1
    assert hits[0].chunk_id == "c1"
