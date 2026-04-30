"""
LLM Wiki 引擎：基于 Karpathy LLM Wiki 模式的知识库管理

三层架构：
- raw/  — 不可变的原始素材
- wiki/ — LLM 维护的结构化 Wiki 页面
- WIKI.md — Schema 约定

三种操作：
- ingest  — 读取 raw/ 中的新文档，提取并整合到 wiki 页面
- query   — 基于 wiki 已编译的知识回答问题
- lint    — 健康检查：矛盾、孤立页面、缺失引用
"""

import os
import re
from datetime import datetime
from pathlib import Path

# ---- 路径 ----
WIKI_ROOT = Path(__file__).parent
RAW_DIR = WIKI_ROOT / "raw"
WIKI_DIR = WIKI_ROOT / "wiki"
SCHEMA_FILE = WIKI_ROOT / "WIKI.md"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
CHROMA_DIR = str(WIKI_ROOT / "chroma_wiki_db")


# ---- Embedding（复用 RAG 模块的模式） ----
def _get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    model_name = "BAAI/bge-small-zh-v1.5"
    try:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu", "local_files_only": False},
            encode_kwargs={"normalize_embeddings": True},
        )


# ---- LLM ----
def _get_llm():
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("MOONSHOT_API_KEY 环境变量未设置")
    return ChatOpenAI(
        model="moonshot-v1-8k",
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )


# ---- 向量数据库 ----
def build_wiki_vector_store(force_rebuild: bool = False) -> "Chroma":
    """构建或加载 wiki 页面的向量数据库"""
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    embeddings = _get_embeddings()

    if not force_rebuild and os.path.exists(CHROMA_DIR):
        return Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )

    # 加载 wiki 目录下的所有 .md 文件
    loader = DirectoryLoader(
        str(WIKI_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    print(f"✅ Wiki 向量数据库构建完成，共 {len(chunks)} 个文本块")
    return vector_store


# ---- 工具函数 ----
def _list_wiki_pages() -> list[Path]:
    """列出所有 wiki 页面"""
    return sorted(WIKI_DIR.rglob("*.md"))


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _append_log(entry: str):
    """追加日志条目"""
    now = datetime.now().strftime("%Y-%m-%d")
    log_entry = f"\n## [{now}] {entry}\n"
    if LOG_FILE.exists():
        current = _read_file(LOG_FILE)
        _write_file(LOG_FILE, current + log_entry)
    else:
        _write_file(LOG_FILE, "# 操作日志\n" + log_entry)


def _extract_wikilinks(content: str) -> list[str]:
    """提取 [[页面名]] 格式的 wikilink"""
    return re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]", content)


def _read_index() -> str:
    """读取 index.md"""
    if INDEX_FILE.exists():
        return _read_file(INDEX_FILE)
    return ""


# ---- Ingest 操作 ----
def ingest(source_path: str) -> str:
    """
    摄入新的原始素材文件，让 LLM 提取关键信息并整合到 wiki。

    Args:
        source_path: raw/ 目录下的文件路径（相对于 wiki 根目录）

    Returns:
        LLM 的摄入报告
    """
    full_path = WIKI_ROOT / source_path
    if not full_path.exists():
        raise FileNotFoundError(f"源文件不存在: {full_path}")

    source_content = _read_file(full_path)
    schema = _read_file(SCHEMA_FILE)
    index = _read_index()

    llm = _get_llm()

    prompt = f"""你是一个 LLM Wiki 维护助手。请根据以下 Schema 约定和现有索引，分析新的原始素材。

## Schema 约定
{schema}

## 当前索引
{index}

## 新原始素材 ({source_path})
{source_content[:8000]}

## 任务
1. 总结这份素材的关键要点（5-10条）
2. 列出应该创建或更新的 wiki 页面（标题、分类、关键内容）
3. 列出与现有页面的交叉引用关系
4. 指出可能的矛盾或需要特别关注的内容

请用中文回答。"""

    messages = [
        {
            "role": "system",
            "content": "你是一个严谨的知识库管理助手，专注于 A 股短线交易策略的知识整理。",
        },
        {"role": "user", "content": prompt},
    ]

    response = llm.invoke(messages)
    report = response.content

    _append_log(
        f"ingest | {source_path}\n- 分析报告已生成\n- 请根据报告更新相关 wiki 页面"
    )

    return report


# ---- Query 操作 ----
def query(question: str, k: int = 5) -> str:
    """
    基于 wiki 知识库回答问题。

    流程：先读取 index.md 定位相关页面，再用向量检索补充，最后用 LLM 综合回答。

    Args:
        question: 用户问题
        k: 检索的文档块数量

    Returns:
        LLM 的回答
    """
    # 1. 读取 index
    index = _read_index()

    # 2. 向量检索
    vector_store = build_wiki_vector_store()
    results = vector_store.similarity_search_with_score(question, k=k)

    context_parts = []
    for doc, score in results:
        source = doc.metadata.get("source", "未知")
        context_parts.append(
            f"[来源: {source} | 相关度: {score:.2f}]\n{doc.page_content}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # 3. LLM 回答
    llm = _get_llm()

    prompt = f"""你是一个连板龙头交易体系的知识库助手。请根据以下 Wiki 索引和检索到的相关内容回答问题。

## Wiki 索引
{index}

## 检索到的相关内容
{context}

## 用户问题
{question}

## 要求
- 基于 wiki 内容回答，不要编造
- 引用具体的 wiki 页面（用 [[页面名]] 格式）
- 如果涉及操作建议，注明风险
- 如果 wiki 中没有相关信息，如实说明"""

    messages = [
        {
            "role": "system",
            "content": "你是一个 A 股连板龙头交易体系的知识助手。回答要精准、实用。",
        },
        {"role": "user", "content": prompt},
    ]

    response = llm.invoke(messages)
    return response.content


# ---- Lint 操作 ----
def lint() -> dict:
    """
    对 wiki 进行健康检查。

    检查项：
    - 孤立页面（无入链）
    - 提到但未创建的页面（悬空链接）
    - 缺失交叉引用
    - 页面统计

    Returns:
        检查报告字典
    """
    pages = _list_wiki_pages()
    report = {
        "total_pages": len(pages),
        "orphan_pages": [],
        "dangling_links": [],
        "pages_with_no_outlinks": [],
        "link_stats": {},
    }

    # 收集所有页面的 wikilink
    page_names = set()
    outlinks = {}  # page -> [linked pages]
    inlinks = {}  # page -> [pages linking to it]

    for page in pages:
        rel_path = page.relative_to(WIKI_DIR)
        name = str(rel_path).replace(".md", "")
        page_names.add(name)
        inlinks.setdefault(name, [])

        content = _read_file(page)
        links = _extract_wikilinks(content)
        outlinks[name] = links

    # 分析链接关系
    all_linked = set()
    # 建立简短名称→完整路径的映射
    short_name_map = {}
    for name in page_names:
        short = name.split("/")[-1]
        short_name_map[short] = name

    for page_name, links in outlinks.items():
        for link in links:
            # 清理链接：移除锚点（#号后的内容）
            clean_link = link.split("#")[0]
            # 规范化：移除 ../ 前缀
            normalized = re.sub(r"^(\.\./)+", "", clean_link)
            all_linked.add(normalized)
            # 尝试解析为完整路径或短名称
            resolved = normalized
            if normalized in short_name_map:
                resolved = short_name_map[normalized]
            inlinks.setdefault(resolved, [])
            inlinks[resolved].append(page_name)

    # 孤立页面（有出链但没有入链）
    for name in page_names:
        if name in ("index", "log", "overview"):
            continue
        if not inlinks.get(name, []):
            report["orphan_pages"].append(name)

    # 悬空链接（引用了但不存在的页面）
    for link in all_linked:
        if not link:  # 跳过空链接（纯锚点）
            continue
        # 直接匹配完整路径
        if link in page_names:
            continue
        # 尝试作为短名称匹配
        if link in short_name_map:
            continue
        # 尝试带路径前缀匹配
        parts = link.split("/")
        if len(parts) >= 2:
            possible = "/".join(parts[-2:])
            if possible in page_names:
                continue
        report["dangling_links"].append(link)

    # 没有出链的页面
    for name, links in outlinks.items():
        if not links and name not in ("log",):
            report["pages_with_no_outlinks"].append(name)

    report["link_stats"] = {
        "total_outlinks": sum(len(v) for v in outlinks.values()),
        "total_unique_pages_linked": len(all_linked),
    }

    return report


def lint_report() -> str:
    """生成可读的 lint 报告"""
    result = lint()

    lines = [
        "# Wiki 健康检查报告",
        f"\n📊 **总页面数**: {result['total_pages']}",
        f"🔗 **总链出数**: {result['link_stats']['total_outlinks']}",
        f"📎 **唯一引用页面**: {result['link_stats']['total_unique_pages_linked']}",
    ]

    if result["orphan_pages"]:
        lines.append(
            f"\n⚠️  **孤立页面**（无入链，共 {len(result['orphan_pages'])} 个）:"
        )
        for p in result["orphan_pages"]:
            lines.append(f"  - {p}")

    if result["dangling_links"]:
        lines.append(
            f"\n❌ **悬空链接**（引用但不存在，共 {len(result['dangling_links'])} 个）:"
        )
        for link in result["dangling_links"]:
            lines.append(f"  - [[{link}]]")

    if result["pages_with_no_outlinks"]:
        lines.append(
            f"\n📭 **无出链页面**（共 {len(result['pages_with_no_outlinks'])} 个）:"
        )
        for p in result["pages_with_no_outlinks"]:
            lines.append(f"  - {p}")

    if not result["orphan_pages"] and not result["dangling_links"]:
        lines.append("\n✅ Wiki 状态健康，无明显问题。")

    _append_log(
        f"lint | 检查完成，{result['total_pages']} 页，{len(result['orphan_pages'])} 孤立，{len(result['dangling_links'])} 悬空"
    )

    return "\n".join(lines)


# ---- CLI ----
if __name__ == "__main__":
    import sys

    usage = """
用法:
    python -m agent.chain.wiki.main query "天量弱转强怎么操作？"
    python -m agent.chain.wiki.main ingest raw/001-连板龙头交易体系.md
    python -m agent.chain.wiki.main lint
    python -m agent.chain.wiki.main build    # 构建/重建向量数据库
    python -m agent.chain.wiki.main pages    # 列出所有 wiki 页面
    """

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    command = sys.argv[1]

    if command == "query":
        if len(sys.argv) < 3:
            print("请提供查询问题")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        print(f"\n🔍 查询: {question}\n")
        print(query(question))

    elif command == "ingest":
        if len(sys.argv) < 3:
            print("请提供源文件路径（相对于 wiki 根目录）")
            sys.exit(1)
        source = sys.argv[2]
        print(f"\n📥 摄入: {source}\n")
        print(ingest(source))

    elif command == "lint":
        print(lint_report())

    elif command == "build":
        print("🔨 构建 Wiki 向量数据库...")
        build_wiki_vector_store(force_rebuild=True)

    elif command == "pages":
        pages = _list_wiki_pages()
        print(f"\n📚 Wiki 页面 (共 {len(pages)} 个):\n")
        for p in pages:
            rel = p.relative_to(WIKI_DIR)
            print(f"  📄 {rel}")

    else:
        print(f"未知命令: {command}")
        print(usage)
        sys.exit(1)
