# Replace ChromaDB with Qdrant

## Goal

Replace the optional wiki/RAG vector store from ChromaDB to Qdrant while preserving the current local, on-disk deployment model and existing command behavior.

## What I already know

- Chroma is used by both `services/agent/chain/wiki/main.py` and `services/agent/chain/rag/main.py`.
- Both stores persist to separate directories mounted as Docker volumes by the optional `rag_agent` profile.
- Wiki and RAG source documents remain available and can regenerate all embeddings.
- The user requested that no code commit be created yet.

## Requirements

- Use Qdrant local on-disk mode; do not add a standalone Qdrant service.
- Preserve existing wiki and RAG build, rebuild, search, and chat command behavior.
- Keep wiki and RAG indexes isolated using explicit persistence paths and collection names.
- Use dense cosine similarity with the existing normalized HuggingFace embeddings.
- Replace Chroma dependencies, imports, type hints, paths, Docker volume names, ignore rules, and documentation references.
- Regenerate `services/agent/poetry.lock` from the dependency change.
- Add narrow tests that do not download a live embedding model or call external services.
- Validate Python tests and Docker Compose configuration.
- Leave all changes uncommitted.

## Acceptance Criteria

- [x] No active source/config/documentation references to Chroma remain, except release/migration notes if needed.
- [x] Wiki and RAG can create an empty Qdrant collection, populate it from documents, reopen it from disk, and rebuild it.
- [x] Existing similarity-search call sites continue returning documents and scores.
- [x] Qdrant persistence directories are excluded from Git and Docker build contexts.
- [x] The optional RAG dependency set installs a LangChain/Qdrant version compatible with `langchain-core<0.4`.
- [x] Relevant tests pass and `docker compose config --quiet` succeeds.
- [x] No `git commit` is created.

## Definition of Done

- Implementation and focused tests are complete.
- Dependency lockfile and operator documentation are updated.
- Quality checks pass or any environmental limitation is reported precisely.
- Git changes remain in the working tree for user review.

## Technical Approach

Create a small shared Qdrant factory in the RAG package that:

- opens a local `QdrantClient(path=...)`;
- creates an explicit collection when absent, using the embedding dimension and cosine distance;
- returns a `QdrantVectorStore` for existing or newly populated collections.

Wiki and RAG retain separate persistence paths and collection names. Existing Chroma data is not converted in place; the reproducible index is rebuilt from source files.

## Decision (ADR-lite)

**Context**: Qdrant supports local embedded storage and a standalone service. The current deployment uses optional local Chroma stores with small datasets and Docker volumes.

**Decision**: Use Qdrant local on-disk mode with `langchain-qdrant>=0.2.0,<0.3.0`.

**Consequences**: Deployment remains simple and offline-capable. The design does not target concurrent multi-process writers or independent Qdrant scaling. Moving to a server later can reuse the same vector-store abstraction with connection configuration.

## Out of Scope

- Running a standalone Qdrant Docker service or Qdrant Cloud.
- Migrating binary Chroma index contents; indexes are rebuilt from source documents.
- Adding sparse or hybrid retrieval.
- Changing embedding models, chunking rules, CLI commands, or RPC/frontend behavior.
- Committing or pushing the changes.

## Research References

- [`research/qdrant-local-migration.md`](research/qdrant-local-migration.md) — compatibility and deployment-mode comparison.

## Technical Notes

- Relevant specs: `.trellis/spec/backend/index.md`, `directory-structure.md`, `quality-guidelines.md`, and shared code-reuse/cross-layer guides.
- Qdrant and LangChain document local disk persistence through `QdrantClient(path=...)`.
- Qdrant local storage should be opened by only one process at a time per path.
