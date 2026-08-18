import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from chain.rag import main as rag_main
from chain.rag.vector_store import open_local_vector_store
from chain.wiki import main as wiki_main

pytest.importorskip("langchain_qdrant")
pytest.importorskip("qdrant_client")


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(lowered.count("涨停")),
            float(lowered.count("风险")),
            float(len(text) or 1),
        ]


def test_local_vector_store_persists_and_reopens(tmp_path):
    store_path = str(tmp_path / "qdrant")
    embeddings = FakeEmbeddings()
    store = open_local_vector_store(
        path=store_path,
        collection_name="test_documents",
        embeddings=embeddings,
    )
    store.add_documents(
        [
            Document(page_content="涨停策略", metadata={"source": "strategy"}),
            Document(page_content="风险控制", metadata={"source": "risk"}),
        ]
    )
    store.client.close()

    reopened = open_local_vector_store(
        path=store_path,
        collection_name="test_documents",
        embeddings=embeddings,
    )
    results = reopened.similarity_search_with_score("涨停", k=1)

    assert results[0][0].metadata["source"] == "strategy"
    assert results[0][0].metadata["_collection_name"] == "test_documents"
    assert isinstance(results[0][1], float)
    reopened.client.close()


def test_local_vector_store_creates_empty_collection(tmp_path):
    store = open_local_vector_store(
        path=str(tmp_path / "empty-qdrant"),
        collection_name="empty_documents",
        embeddings=FakeEmbeddings(),
    )

    assert store.client.collection_exists("empty_documents")
    assert store.similarity_search("涨停", k=1) == []
    store.client.close()


def test_rag_rebuild_replaces_existing_documents(tmp_path, monkeypatch):
    store_path = str(tmp_path / "rag-qdrant")
    embeddings = FakeEmbeddings()
    documents = [Document(page_content="涨停策略", metadata={"version": "old"})]
    monkeypatch.setattr(rag_main, "QDRANT_PERSIST_DIR", store_path)
    monkeypatch.setattr(rag_main, "get_embeddings", lambda: embeddings)
    monkeypatch.setattr(rag_main, "load_documents", lambda: documents)
    monkeypatch.setattr(rag_main, "split_documents", lambda docs: docs)

    initial = rag_main.build_vector_store()
    assert initial.similarity_search("涨停", k=1)[0].metadata["version"] == "old"
    initial.client.close()

    documents[:] = [Document(page_content="风险控制", metadata={"version": "new"})]
    rebuilt = rag_main.build_vector_store(force_rebuild=True)
    results = rebuilt.similarity_search("风险", k=2)

    assert [result.metadata["version"] for result in results] == ["new"]
    rebuilt.client.close()


def test_wiki_vector_store_builds_and_reopens(tmp_path, monkeypatch):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "overview.md").write_text("涨停策略", encoding="utf-8")
    store_path = str(tmp_path / "wiki-qdrant")
    monkeypatch.setattr(wiki_main, "WIKI_DIR", wiki_dir)
    monkeypatch.setattr(wiki_main, "QDRANT_DIR", store_path)
    monkeypatch.setattr(wiki_main, "_get_embeddings", FakeEmbeddings)

    built = wiki_main.build_wiki_vector_store()
    assert (
        built.similarity_search("涨停", k=1)[0]
        .metadata["source"]
        .endswith("overview.md")
    )
    built.client.close()

    reopened = wiki_main.build_wiki_vector_store()
    assert reopened.similarity_search("涨停", k=1)
    reopened.client.close()
