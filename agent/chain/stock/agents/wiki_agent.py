"""
Stock Wiki Agent

为 stock 模块提供统一的 wiki 调用入口，屏蔽底层 wiki 实现细节。
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StockWikiAgent:
    """stock 侧的 wiki 适配器。"""

    def __init__(self):
        self._wiki_main = None

    def _load_wiki(self):
        if self._wiki_main is None:
            from chain.wiki import main as wiki_main

            self._wiki_main = wiki_main
        return self._wiki_main

    def query(self, question: str, k: int = 5) -> str:
        """基于 wiki 回答问题。"""
        wiki_main = self._load_wiki()
        return wiki_main.query(question, k=k)

    def ingest(self, source_path: str) -> str:
        """摄入 raw 素材并生成分析报告。"""
        wiki_main = self._load_wiki()
        return wiki_main.ingest(source_path)

    def lint(self) -> str:
        """运行 wiki 健康检查并返回可读报告。"""
        wiki_main = self._load_wiki()
        return wiki_main.lint_report()

    def build(self) -> str:
        """重建 wiki 向量索引。"""
        wiki_main = self._load_wiki()
        wiki_main.build_wiki_vector_store(force_rebuild=True)
        return "✅ Wiki 向量数据库构建完成"

    def pages(self) -> list[str]:
        """列出 wiki 页面路径（相对 wiki 目录）。"""
        wiki_main = self._load_wiki()
        pages = wiki_main._list_wiki_pages()
        return [str(Path(p).relative_to(wiki_main.WIKI_DIR)) for p in pages]


def create_wiki_agent() -> StockWikiAgent:
    """工厂函数：创建 stock wiki 适配器。"""
    return StockWikiAgent()
