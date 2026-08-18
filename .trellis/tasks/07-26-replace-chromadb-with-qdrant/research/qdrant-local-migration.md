# Qdrant Local Migration Research

## Sources

- Qdrant LangChain integration: https://qdrant.tech/documentation/frameworks/langchain/
- LangChain Qdrant integration: https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant
- PyPI package metadata:
  - `langchain-qdrant==0.2.1` supports `langchain-core>=0.2.43,<0.4.0`
  - `langchain-qdrant==1.1.0` requires `langchain-core>=1.0.0`

## Repository constraints

- Wiki and RAG currently use separate Chroma persistence directories and Docker volumes.
- The optional `rag_agent` image keeps heavyweight vector-search dependencies out of the stock-agent image.
- Source Markdown/text files remain available, so vector indexes are reproducible.
- The project pins `langchain-core>=0.3.78,<0.4.0`, making `langchain-qdrant>=0.2.0,<0.3.0` the compatible integration line.

## Feasible approaches

### A. Qdrant local on-disk mode

- Use `QdrantClient(path=...)` and `QdrantVectorStore`.
- Preserve separate on-disk stores and Docker volumes for wiki and RAG.
- No additional network service, credentials, ports, or health checks.
- Best match for the current small, optional, single-process RAG deployment.

### B. Dedicated Qdrant server

- Add a Qdrant Docker service and connect `rag_agent` over HTTP or gRPC.
- Better for concurrent writers, larger datasets, and independent scaling.
- Adds service lifecycle, ports, health checks, configuration, and deployment overhead.

## Recommendation

Use approach A for this migration. Keep collection names explicit, create collections with cosine distance and the current embedding dimension, and treat old Chroma indexes as disposable derived data. Operators rebuild Qdrant indexes from source documents after upgrading.

