"""
LLM Wiki 模块 — 基于 Karpathy LLM Wiki 模式的连板龙头交易知识库

三层架构：raw（原始素材）→ wiki（结构化页面）→ WIKI.md（schema）

操作：
- ingest: 摄入新素材
- query: 基于知识库查询
- lint: 健康检查
"""


def __getattr__(name):
    from importlib import import_module

    main = import_module(".main", __name__)
    return getattr(main, name)


__all__ = [
    "ingest",
    "query",
    "lint",
    "lint_report",
    "build_wiki_vector_store",
]
