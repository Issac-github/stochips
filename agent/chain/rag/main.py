"""
RAG 模块：基于本地向量数据库 + LangChain 实现检索增强生成

- 向量数据库：ChromaDB（本地持久化）
- Embedding 模型：HuggingFace 本地模型（BAAI/bge-small-zh-v1.5，适合中文）
- 文档来源：rag/ 目录下的 .md 文件
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings

# 项目路径
RAG_DIR = Path(__file__).parent
CHROMA_PERSIST_DIR = str(RAG_DIR / "chroma_db")

# 本地 Embedding 模型，首次运行会自动下载
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 模型大小约 1.5GB
# EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 只需 800MB


def _clear_directory_contents(path: str):
    """清空目录内容但保留目录本身，兼容 Docker volume 挂载点。"""
    target = Path(path)
    if not target.exists():
        return
    for child in target.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _create_embeddings(local_files_only: bool) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu", "local_files_only": local_files_only},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """获取本地 HuggingFace Embedding 模型"""
    # 优先离线加载：命中缓存时不会访问 HuggingFace。
    try:
        return _create_embeddings(local_files_only=True)
    except Exception:
        print("ℹ️ 本地缓存未命中，尝试联网下载模型...")
        return _create_embeddings(local_files_only=False)


def load_documents():
    """加载 rag/ 目录下所有 .md/.txt 文件"""
    docs = []
    for glob in ("**/*.md", "**/*.txt"):
        loader = DirectoryLoader(
            str(RAG_DIR),
            glob=glob,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        docs.extend(loader.load())
    if not docs:
        print("⚠️  rag/ 目录下没有找到 .md/.txt 文件或文件内容为空")
        return []
    return docs


_SENTENCE_END_RE = re.compile(r"[。！？!?；;]$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*")
_STEP_RE = re.compile(r"^(第[一二三四五六七八九十]+[:：]|[0-9]+[.、)]\s*|[一二三四五六七八九十]+[、.]\s*)")
_DEFINITION_RE = re.compile(r"(.{1,40}?)(是指|指的是|本质上是|意味着|说明|就是|定义为)(.+)")
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_LIST_ITEM_RE = re.compile(r"^([-*+]\s+|[0-9]+[.、)]\s+)")
_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_LINK_RE = re.compile(r"\[([^\]]+)]\([^)]+\)")
_TOPIC_KEYWORDS = {
    "龙头": ("龙头", "总龙头", "老龙头", "新龙头", "空间板", "空间龙头"),
    "弱转强": ("弱转强", "抢筹", "高开", "翻红", "泛红", "竞价"),
    "一字助攻": ("一字", "助攻", "顶一字"),
    "情绪周期": ("情绪", "复苏", "退潮", "涨潮", "周期", "气氛"),
    "主线板块": ("主线", "主流", "板块", "题材", "梯队"),
    "预期": ("预期", "超预期", "不及预期", "低于预期"),
    "进出点": ("进点", "出点", "卖点", "买入", "起票", "开仓", "止盈", "止损"),
    "仓位管理": ("仓位", "重仓", "半仓", "三层", "七层", "减仓", "加仓", "顺踢"),
    "缺口": ("缺口", "加速缺口", "逃逸缺口"),
    "复盘": ("复盘", "高标池", "目标池", "指标预警", "自选"),
}


@dataclass
class SemanticUnit:
    text: str
    section_path: tuple[str, ...]
    kind: str
    topics: set[str] = field(default_factory=set)


@dataclass
class SemanticChunk:
    units: list[SemanticUnit]

    @property
    def text(self) -> str:
        return "\n".join(unit.text for unit in self.units).strip()

    @property
    def section_path(self) -> tuple[str, ...]:
        return self.units[0].section_path if self.units else ()

    @property
    def topics(self) -> set[str]:
        topics = set()
        for unit in self.units:
            topics.update(unit.topics)
        return topics

    @property
    def kinds(self) -> set[str]:
        return {unit.kind for unit in self.units}


def _clean_text(text: str) -> str:
    """轻度清洗文本：只规范空白和不可见字符，不改写事实。"""
    text = text.replace("\ufeff", "").replace("\u200b", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    cleaned_lines = []
    blank_seen = False
    for line in lines:
        if not line:
            if not blank_seen:
                cleaned_lines.append("")
            blank_seen = True
            continue
        cleaned_lines.append(line)
        blank_seen = False
    return "\n".join(cleaned_lines).strip()


def _logical_lines(text: str) -> list[str]:
    """把被硬换行打断的同一句合并，同时保留标题、列表和表格边界。"""
    raw_lines = [line for line in text.splitlines() if line.strip()]
    lines: list[str] = []
    for line in raw_lines:
        if (
            lines
            and not _is_heading(lines[-1])
            and not _is_heading(line)
            and not _looks_like_table_row(lines[-1])
            and not _looks_like_table_row(line)
            and not _TABLE_SEPARATOR_RE.match(lines[-1])
            and not _TABLE_SEPARATOR_RE.match(line)
            and not _LIST_ITEM_RE.match(line)
            and not _STEP_RE.match(line)
            and not _SENTENCE_END_RE.search(lines[-1])
        ):
            separator = " " if re.search(r"[A-Za-z0-9]$", lines[-1]) and re.match(r"^[A-Za-z0-9]", line) else ""
            lines[-1] = f"{lines[-1]}{separator}{line}"
        else:
            lines.append(line)
    return lines


def _is_heading(line: str) -> bool:
    """识别主题标题，兼容 Markdown 标题和当前 doc.md 里的短标题。"""
    if _MARKDOWN_HEADING_RE.match(line):
        return True
    if re.fullmatch(r"【[^】]{1,30}】", line):
        return True
    if line.startswith(("-", "*", "|", ">")) or _STEP_RE.match(line):
        return False
    if _SENTENCE_END_RE.search(line):
        return False
    return len(line) <= 18


def _heading_level(line: str) -> int:
    markdown_heading = _MARKDOWN_HEADING_RE.match(line)
    if markdown_heading:
        return len(markdown_heading.group(1))
    if re.fullmatch(r"【[^】]{1,30}】", line):
        return 2
    return 1


def _normalize_heading(line: str) -> str:
    markdown_heading = _MARKDOWN_HEADING_RE.match(line)
    if markdown_heading:
        return markdown_heading.group(2).strip()
    return line.strip(" #【】")


def _push_heading(section_stack: list[tuple[int, str]], line: str) -> list[tuple[int, str]]:
    level = _heading_level(line)
    heading = _normalize_heading(line)
    if not heading:
        return section_stack
    return [item for item in section_stack if item[0] < level] + [(level, heading)]


def _section_path(section_stack: list[tuple[int, str]]) -> tuple[str, ...]:
    return tuple(heading for _, heading in section_stack) or ("全文",)


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    parts = _SENTENCE_SPLIT_RE.split(normalized)
    sentences = [part.strip() for part in parts if part.strip()]
    if len(sentences) <= 1 and len(normalized) > 140:
        sentences = [part.strip() for part in re.split(r"(?<=[，,])\s*", normalized) if part.strip()]
    return sentences


def _summarize_extractive(text: str, max_chars: int = 120) -> str:
    """抽取式摘要：只使用原文开头句子，不新增事实。"""
    summary = ""
    for sentence in _split_sentences(text):
        if len(summary) + len(sentence) > max_chars:
            break
        summary += sentence
    return summary or text[:max_chars]


def _looks_like_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def _table_to_sentences(lines: list[str]) -> list[str]:
    rows = []
    for line in lines:
        if _TABLE_SEPARATOR_RE.match(line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if any(cells):
            rows.append(cells)

    if not rows:
        return []
    headers = rows[0]
    sentences = []
    for row in rows[1:]:
        pairs = []
        for index, cell in enumerate(row):
            header = headers[index] if index < len(headers) and headers[index] else f"第{index + 1}列"
            if cell:
                pairs.append(f"{header}为{cell}")
        if pairs:
            sentences.append("表格行：" + "；".join(pairs) + "。")
    return sentences


def _normalize_list_item(line: str) -> str:
    if _STEP_RE.match(line):
        return "步骤：" + _STEP_RE.sub("", line, count=1).strip()
    if _LIST_ITEM_RE.match(line):
        return "列表项：" + _LIST_ITEM_RE.sub("", line, count=1).strip()
    return line


def _detect_topics(text: str, section_path: tuple[str, ...]) -> set[str]:
    target = " ".join((*section_path, text))
    return {
        topic
        for topic, keywords in _TOPIC_KEYWORDS.items()
        if any(keyword in target for keyword in keywords)
    }


def _unit_kind(text: str) -> str:
    if "？" in text or "?" in text:
        return "faq"
    if text.startswith("步骤：") or _STEP_RE.match(text):
        return "steps"
    if _DEFINITION_RE.search(text):
        return "definition"
    if any(keyword in text for keyword in ("必须", "不要", "需要", "原则", "如果", "当", "只有", "标准")):
        return "rules"
    return "semantic"


def _chunk_kind(chunk: SemanticChunk) -> str:
    kinds = chunk.kinds
    for kind in ("faq", "steps", "definition", "rules"):
        if kind in kinds:
            return kind
    return "semantic"


def _make_title(section_path: tuple[str, ...], text: str, topics: set[str]) -> str:
    sentences = _split_sentences(text)
    first_sentence = sentences[0] if sentences else text
    phrase = re.split(r"[，,。；;：:]", first_sentence)[0].strip(" -_*")
    section = " / ".join(section_path)
    topic = "、".join(sorted(topics)[:2])
    if topic and topic not in section:
        return f"{section} - {topic} - {phrase[:24]}"
    if phrase and phrase != section:
        return f"{section} - {phrase[:30]}"
    return section or "未命名片段"


def _make_unit(text: str, section_path: tuple[str, ...], kind: str | None = None) -> SemanticUnit:
    text = text.strip()
    unit_kind = kind or _unit_kind(text)
    return SemanticUnit(
        text=text,
        section_path=section_path,
        kind=unit_kind,
        topics=_detect_topics(text, section_path),
    )


def _document_units(doc: Document) -> list[SemanticUnit]:
    text = _clean_text(doc.page_content)
    lines = _logical_lines(text)
    units = []
    section_stack: list[tuple[int, str]] = []
    table_buffer = []

    def flush_table():
        nonlocal table_buffer
        if table_buffer:
            path = _section_path(section_stack)
            for sentence in _table_to_sentences(table_buffer):
                units.append(_make_unit(sentence, path, kind="table"))
            table_buffer = []

    for line in lines:
        if _looks_like_table_row(line) or _TABLE_SEPARATOR_RE.match(line):
            table_buffer.append(line)
            continue

        flush_table()
        if _is_heading(line):
            section_stack = _push_heading(section_stack, line)
            continue

        path = _section_path(section_stack)
        normalized_line = _normalize_list_item(line)
        if normalized_line.startswith(("列表项：", "步骤：")):
            units.append(_make_unit(normalized_line, path))
            continue

        for sentence in _split_sentences(normalized_line):
            units.append(_make_unit(sentence, path))

    flush_table()
    return units


def _is_topic_shift(current: SemanticChunk, unit: SemanticUnit) -> bool:
    if unit.section_path != current.section_path:
        return True
    if not unit.topics or not current.topics:
        return False
    return current.topics.isdisjoint(unit.topics)


def _merge_units(units: list[SemanticUnit], chunk_size: int, min_chunk_size: int) -> list[SemanticChunk]:
    """按章节、主题关键词和长度合并，避免硬按字符截断。"""
    chunks: list[SemanticChunk] = []
    current: SemanticChunk | None = None

    for unit in units:
        if current is None:
            current = SemanticChunk(units=[unit])
            continue

        next_len = len(current.text) + 1 + len(unit.text)
        topic_shift = _is_topic_shift(current, unit)
        enough_units = len(current.units) >= 8 and len(current.text) >= min_chunk_size
        too_large = next_len > chunk_size and len(current.text) >= min_chunk_size
        should_start_new = topic_shift or too_large or enough_units

        if should_start_new:
            chunks.append(current)
            current = SemanticChunk(units=[unit])
        else:
            current.units.append(unit)

    if current:
        chunks.append(current)
    return chunks


def _merge_tiny_chunks(
    chunks: list[SemanticChunk],
    min_chunk_size: int,
    max_chunk_size: int,
) -> list[SemanticChunk]:
    if not chunks:
        return []
    merged: list[SemanticChunk] = []
    for chunk in chunks:
        can_merge = (
            merged
            and chunk.section_path == merged[-1].section_path
            and len(merged[-1].text) + 1 + len(chunk.text) <= int(max_chunk_size * 1.25)
        )
        if (
            can_merge
            and len(chunk.text) < min_chunk_size
        ):
            merged[-1].units.extend(chunk.units)
        elif can_merge and len(merged[-1].text) < min_chunk_size:
            merged[-1].units.extend(chunk.units)
        else:
            merged.append(chunk)
    return merged


def _build_semantic_document(
    source_doc: Document,
    chunk: SemanticChunk,
    index: int,
    total: int,
    previous_title: str | None,
) -> Document:
    raw_content = chunk.text
    section_path = chunk.section_path
    section = " / ".join(section_path)
    topics = sorted(chunk.topics)
    title = _make_title(section_path, raw_content, chunk.topics)
    summary = _summarize_extractive(raw_content)
    block_type = _chunk_kind(chunk)

    parts = [
        f"标题：{title}",
        f"主题：{section}",
    ]
    if topics:
        parts.append(f"关键词：{'、'.join(topics)}")
    parts.append(raw_content)

    metadata = {
        **source_doc.metadata,
        "chunk_index": index,
        "chunk_total": total,
        "chunk_id": f"{source_doc.metadata.get('source', 'doc')}#{index}",
        "previous_chunk_id": f"{source_doc.metadata.get('source', 'doc')}#{index - 1}" if index > 0 else "",
        "next_chunk_id": f"{source_doc.metadata.get('source', 'doc')}#{index + 1}" if index + 1 < total else "",
        "previous_title": previous_title or "",
        "semantic_title": title,
        "section": section,
        "summary": summary,
        "block_type": block_type,
        "topics": ",".join(topics),
        "unit_kinds": ",".join(sorted(chunk.kinds)),
    }
    return Document(page_content="\n".join(parts), metadata=metadata)


def split_documents(docs, chunk_size=560, chunk_overlap=100, min_chunk_size=160):
    """
    语义切分 / 清洗 / 摘要 / 提取标题。

    处理原则：
    - 只切分和轻度整理，不新增事实、不省略关键信息。
    - 按标题层级、主题关键词和语义句子组织段落。
    - 合并太短碎片，避免把不相关主题硬塞进同一块。
    - 标题、摘要、上下文关系主要进入 metadata，embedding 文本以原文事实为主。
    - FAQ、定义、条款、步骤、表格、列表会被标注为不同 unit 类型。
    """
    # 保留 chunk_overlap 参数以兼容旧调用；上下文通过上文摘要和前后块 id 表达。
    _ = chunk_overlap
    semantic_docs = []

    for doc in docs:
        units = _document_units(doc)
        if not units:
            continue

        chunks = _merge_tiny_chunks(
            _merge_units(units, chunk_size=chunk_size, min_chunk_size=min_chunk_size),
            min_chunk_size=min_chunk_size,
            max_chunk_size=chunk_size,
        )
        previous_title = None
        for index, chunk in enumerate(chunks):
            semantic_doc = _build_semantic_document(
                source_doc=doc,
                chunk=chunk,
                index=index,
                total=len(chunks),
                previous_title=previous_title,
            )
            semantic_docs.append(semantic_doc)
            previous_title = semantic_doc.metadata["semantic_title"]

    return semantic_docs


def build_vector_store(force_rebuild: bool = False) -> Chroma:
    """
    构建或加载向量数据库

    Args:
        force_rebuild: 是否强制重建（忽略已有数据库）

    Returns:
        Chroma 向量数据库实例
    """
    embeddings = get_embeddings()

    # 如果已有持久化数据库且不强制重建，直接加载
    if not force_rebuild and os.path.exists(CHROMA_PERSIST_DIR):
        print("📂 加载已有向量数据库...")
        return Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
        )
    if force_rebuild and os.path.exists(CHROMA_PERSIST_DIR):
        print("🧹 清理旧向量数据库...")
        _clear_directory_contents(CHROMA_PERSIST_DIR)

    # 重新构建
    print("📄 加载文档...")
    docs = load_documents()
    if not docs:
        # 返回空的向量数据库
        return Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
        )

    print(f"✂️  分割文档，共 {len(docs)} 个文件...")
    chunks = split_documents(docs)
    print(f"📦 共生成 {len(chunks)} 个文本块")

    print("🔨 构建向量数据库...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print(f"✅ 向量数据库构建完成，存储于 {CHROMA_PERSIST_DIR}")
    return vector_store


def query_rag(question: str, k: int = 3) -> list[dict]:
    """
    检索相关文档

    Args:
        question: 查询问题
        k: 返回的相关文档数量

    Returns:
        相关文档列表，每项包含 content 和 metadata
    """
    vector_store = build_vector_store()
    results = vector_store.similarity_search_with_score(question, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        }
        for doc, score in results
    ]


# ---- 以下为结合 LLM 的完整 RAG 问答 ----


def rag_chat(question: str, k: int = 3) -> str:
    """
    RAG 问答：检索相关文档 + LLM 生成回答

    使用 Moonshot (Kimi) 作为 LLM，需要配置 MOONSHOT_API_KEY 环境变量

    Args:
        question: 用户问题
        k: 检索文档数量

    Returns:
        LLM 生成的回答
    """
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()

    moonshot_api_key = os.getenv("MOONSHOT_API_KEY")
    if not moonshot_api_key:
        raise ValueError("MOONSHOT_API_KEY 环境变量未设置")

    # 检索相关文档
    results = query_rag(question, k=k)
    if not results:
        return "未找到相关文档内容，请确保 rag/ 目录下有 .md 文件并重新构建向量数据库。"

    # 拼接上下文
    context = "\n\n---\n\n".join(
        f"[来源: {r['metadata'].get('source', '未知')}]\n{r['content']}"
        for r in results
    )

    # 构建 LLM
    llm = ChatOpenAI(
        model="moonshot-v1-8k",
        api_key=moonshot_api_key,
        base_url="https://api.moonshot.cn/v1",
    )

    # 构建 Prompt
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个知识问答助手。请根据以下参考资料回答用户问题。"
                "如果参考资料中没有相关信息，请如实说明。"
                "不要编造答案。\n\n"
                f"参考资料：\n{context}"
            ),
        },
        {"role": "user", "content": question},
    ]

    response = llm.invoke(messages)
    return response.content


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m rag.main build          # 构建向量数据库")
        print("  python -m rag.main rebuild         # 强制重建向量数据库")
        print("  python -m rag.main search <问题>   # 检索相关文档")
        print("  python -m rag.main chat <问题>     # RAG 问答")
        sys.exit(1)

    command = sys.argv[1]

    if command == "build":
        build_vector_store()
    elif command == "rebuild":
        build_vector_store(force_rebuild=True)
    elif command == "search" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        results = query_rag(q)
        for i, r in enumerate(results, 1):
            print(f"\n--- 结果 {i} (距离分数: {r['score']:.4f}，越小越相关) ---")
            print(f"来源: {r['metadata'].get('source', '未知')}")
            print(f"内容: {r['content'][:200]}...")
    elif command == "chat" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        answer = rag_chat(q)
        print(f"\n回答：{answer}")
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
