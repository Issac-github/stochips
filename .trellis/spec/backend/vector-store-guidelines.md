# Backend Vector Store Guidelines

## Scenario: Local Qdrant for Wiki and RAG

### 1. Scope / Trigger

- Trigger: changes to wiki/RAG vector persistence, embedding dimensions, collection names, retrieval scores, optional RAG dependencies, or Docker volume wiring.
- Ownership stays in `services/agent/chain/rag/` and `services/agent/chain/wiki/`.
- Keep Qdrant, HuggingFace, and Torch behind the optional `rag` extra and `rag_agent` Docker profile.

### 2. Signatures

- `open_local_vector_store(*, path: str, collection_name: str, embeddings: Embeddings) -> QdrantVectorStore`
- `build_vector_store(force_rebuild: bool = False) -> QdrantVectorStore`
- `build_wiki_vector_store(force_rebuild: bool = False) -> QdrantVectorStore`
- `query_rag(question: str, k: int = 3) -> list[dict]`

### 3. Contracts

- Use `langchain-qdrant>=0.2.0,<0.3.0` while the project remains on `langchain-core>=0.3.78,<0.4.0`.
- Use Qdrant local on-disk mode through `QdrantClient(path=...)`; do not add a network service for the current small, single-process deployment.
- RAG path and collection: `chain/rag/qdrant_db`, `rag_documents`.
- Wiki path and collection: `chain/wiki/qdrant_wiki_db`, `wiki_documents`.
- Create collections with the active embedding dimension and `Distance.COSINE`.
- `similarity_search_with_score` returns a similarity score where larger values are more relevant.
- Qdrant adds `_id` and `_collection_name` to retrieved document metadata; callers must read their own metadata keys without requiring exact dictionary equality.
- Docker volumes are derived indexes. Source wiki/RAG documents are authoritative, so replacing an old backend rebuilds indexes instead of converting backend-specific files.
- No new environment key is required for local mode.

### 4. Validation & Error Matrix

- Persistence directory absent -> create the directory and collection.
- Directory exists but collection is absent -> create the collection.
- Source document list is empty -> return a valid empty collection.
- `force_rebuild=True` -> clear only the selected persistence directory, recreate its collection, and index current source documents.
- Qdrant optional packages absent -> non-RAG stock commands remain importable; the wiki/RAG command that opens the store reports the dependency import failure.
- Two processes open the same local Qdrant path -> Qdrant may reject the second lock; run one wiki/RAG command per path at a time or move to a Qdrant server in a separately designed change.
- Embedding dimension changes against an existing collection -> rebuild the affected index; do not suppress Qdrant's dimension validation.

### 5. Good/Base/Bad Cases

- Good: `rebuild` clears one Qdrant volume path and retrieval returns only newly indexed documents.
- Base: a later command reopens the existing collection and retrieves persisted documents.
- Base: no source documents creates an empty searchable collection without error.
- Bad: detecting only that the directory exists and assuming its collection exists.
- Bad: sharing one local Qdrant path between wiki and RAG or opening it from concurrent processes.
- Bad: displaying a Qdrant similarity score as a distance where smaller means more relevant.
- Bad: installing Qdrant into the default `stock_agent` image.

### 6. Tests Required

- Use deterministic fake embeddings; never download a live HuggingFace model in unit tests.
- Assert an empty local collection can be created and queried.
- Add documents, close the client, reopen the same path, and assert content plus business metadata persisted.
- Force rebuild and assert old documents are absent and current documents are present.
- Exercise both the RAG and wiki builders.
- Close local Qdrant clients in tests so temporary-directory cleanup does not retain a file lock.
- Skip Qdrant-specific tests when the optional `rag` dependency set is not installed; run them in the RAG-enabled quality job.

### 7. Wrong vs Correct

Wrong:

```python
if os.path.exists(path):
    return QdrantVectorStore.from_existing_collection(...)
```

This fails for a newly mounted, empty Docker volume and does not establish the vector dimension or distance.

Correct:

```python
client = QdrantClient(path=path)
if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=len(embeddings.embed_query("vector dimension probe")),
            distance=Distance.COSINE,
        ),
    )
return QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=embeddings,
)
```
