__all__ = ["build_vector_store", "query_rag", "rag_chat"]


def __getattr__(name):
    if name in __all__:
        from .main import build_vector_store, query_rag, rag_chat

        return {
            "build_vector_store": build_vector_store,
            "query_rag": query_rag,
            "rag_chat": rag_chat,
        }[name]
    raise AttributeError(f"module 'rag' has no attribute {name!r}")
