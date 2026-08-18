"""Shared helpers for local, on-disk Qdrant vector stores."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_qdrant import QdrantVectorStore


def open_local_vector_store(
    *,
    path: str,
    collection_name: str,
    embeddings: "Embeddings",
) -> "QdrantVectorStore":
    """Open a local Qdrant store, creating its collection when necessary."""
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    Path(path).mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=path)
    if not client.collection_exists(collection_name):
        dimension_probe = embeddings.embed_query("vector dimension probe")
        vector_size = len(dimension_probe)
        vectors_config = VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        )
        client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
        )

    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
