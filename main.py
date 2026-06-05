from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.chunking import (
    EnsembleChunker,
    FixedSizeChunker,
    HybridLegalChunker,
    LegalChunker,
    RecursiveChunker,
    SentenceChunker,
)
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

SAMPLE_FILES = [
    "data/kehoach199.txt",
    "data/luatchuyendoiso2025.txt",
    "data/luatthihanhandansu2025.txt",
    "data/nghidinh161-2026.txt",
    "data/thongtu29-2026.txt",
]

DEFAULT_CHUNK_STRATEGY = "ensemble"

AVAILABLE_STRATEGIES = {
    "fixed": "Fixed-size chunking with overlap",
    "sentence": "Sentence-based chunking",
    "recursive": "Recursive separator-based chunking",
    "legal": "Legal-structure-aware chunking by chapter/article markers",
    "hybrid": "Hybrid legal chunking: section markers first, sentence refinement second",
    "ensemble": "Combined strategy: sentence + legal + recursive with deduplication",
}

LEGAL_FILE_METADATA = {
    "kehoach199": {
        "title": "Kế hoạch 199/KH-UBND",
        "doc_type": "plan",
        "topic": "anti_drug_policy",
        "year": 2026,
        "language": "vi",
    },
    "luatchuyendoiso2025": {
        "title": "Luật Chuyển đổi số 2025",
        "doc_type": "law",
        "topic": "digital_transformation",
        "year": 2025,
        "language": "vi",
    },
    "luatthihanhandansu2025": {
        "title": "Luật Thi hành án dân sự 2025",
        "doc_type": "law",
        "topic": "civil_enforcement",
        "year": 2025,
        "language": "vi",
    },
    "nghidinh161-2026": {
        "title": "Nghị định 161/2026/NĐ-CP",
        "doc_type": "decree",
        "topic": "base_salary",
        "year": 2026,
        "language": "vi",
    },
    "thongtu29-2026": {
        "title": "Thông tư 29/2026/TT-BCT",
        "doc_type": "circular",
        "topic": "electricity_market",
        "year": 2026,
        "language": "vi",
    },
}

PHASE2_BENCHMARKS = [
    {
        "query": "Luật Chuyển đổi số 2025 quy định phạm vi điều chỉnh như thế nào?",
        "expected_doc_id": "luatchuyendoiso2025",
        "gold_answer": (
            "Luật quy định về chuyển đổi số, bao gồm nguyên tắc, chính sách, điều phối quốc gia, "
            "biện pháp bảo đảm, Chính phủ số, kinh tế số, xã hội số, và trách nhiệm của cơ quan, "
            "tổ chức, cá nhân trong chuyển đổi số."
        ),
    },
    {
        "query": "Nghị định 161/2026 quy định mức lương cơ sở từ ngày nào và là bao nhiêu?",
        "expected_doc_id": "nghidinh161-2026",
        "gold_answer": "Từ ngày 01/7/2026, mức lương cơ sở là 2.530.000 đồng/tháng.",
    },
    {
        "query": "Thông tư 29/2026 điều chỉnh những nội dung chính nào của thị trường bán buôn điện cạnh tranh?",
        "expected_doc_id": "thongtu29-2026",
        "gold_answer": (
            "Thông tư quy định đăng ký tham gia thị trường điện, lập kế hoạch vận hành, cơ chế chào giá, "
            "lập lịch huy động, đo đếm điện năng, xác định giá thị trường và thanh toán, công bố thông tin, "
            "giám sát vận hành, và trách nhiệm của các đơn vị tham gia thị trường điện."
        ),
    },
    {
        "query": "Luật Thi hành án dân sự 2025 quy định ai có thẩm quyền giải quyết khiếu nại lần hai?",
        "expected_doc_id": "luatthihanhandansu2025",
        "gold_answer": (
            "Thủ trưởng cơ quan quản lý thi hành án dân sự thuộc Bộ Tư pháp giải quyết khiếu nại lần hai "
            "đối với quyết định giải quyết khiếu nại chưa có hiệu lực thi hành của Thủ trưởng cơ quan thi "
            "hành án dân sự tỉnh, thành phố và của Trưởng văn phòng thi hành án dân sự."
        ),
    },
    {
        "query": "Kế hoạch 199/KH-UBND năm 2026 hướng tới mục tiêu tổng quát nào?",
        "expected_doc_id": "kehoach199",
        "gold_answer": (
            "Huy động sức mạnh tổng hợp của hệ thống chính trị và toàn dân tham gia phòng, chống tội phạm "
            "và tệ nạn ma túy; từng bước xây dựng và duy trì bền vững xã, phường không ma túy trong giai đoạn "
            "2026-2030, hướng tới xây dựng tỉnh không ma túy."
        ),
    },
]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_documents_from_files(file_paths: list[str]) -> list[Document]:
    """Load documents from file paths for the manual demo."""
    allowed_extensions = {".md", ".txt"}
    documents: list[Document] = []

    for raw_path in file_paths:
        path = Path(raw_path)

        if path.suffix.lower() not in allowed_extensions:
            print(f"Skipping unsupported file type: {path} (allowed: .md, .txt)")
            continue

        if not path.exists() or not path.is_file():
            print(f"Skipping missing file: {path}")
            continue

        content = path.read_text(encoding="utf-8")
        metadata = {"source": str(path), "extension": path.suffix.lower()}
        metadata.update(LEGAL_FILE_METADATA.get(path.stem, {}))
        documents.append(
            Document(
                id=path.stem,
                content=content,
                metadata=metadata,
            )
        )

    return documents


def get_chunker(strategy: str):
    strategy_name = strategy.strip().lower()
    if strategy_name == "fixed":
        return FixedSizeChunker(chunk_size=500, overlap=50)
    if strategy_name == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    if strategy_name == "recursive":
        return RecursiveChunker(chunk_size=500)
    if strategy_name == "legal":
        return LegalChunker(chunk_size=500)
    if strategy_name == "hybrid":
        return HybridLegalChunker(chunk_size=500, max_sentences_per_chunk=2)
    if strategy_name == "ensemble":
        return EnsembleChunker(chunk_size=500, max_sentences_per_chunk=2)
    raise ValueError(f"Unknown strategy: {strategy}")


def build_chunked_documents(documents: list[Document], strategy: str) -> list[Document]:
    chunker = get_chunker(strategy)
    chunked_documents: list[Document] = []

    for document in documents:
        chunks = chunker.chunk(document.content)
        for chunk_index, chunk_text in enumerate(chunks):
            metadata = dict(document.metadata)
            metadata["doc_id"] = document.id
            metadata["chunk_index"] = chunk_index
            metadata["chunk_strategy"] = strategy
            chunked_documents.append(
                Document(
                    id=f"{document.id}_chunk_{chunk_index}",
                    content=chunk_text,
                    metadata=metadata,
                )
            )

    return chunked_documents


def demo_llm(prompt: str) -> str:
    """A simple mock LLM for manual RAG testing."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def run_manual_demo(question: str | None = None, sample_files: list[str] | None = None) -> int:
    files = sample_files or SAMPLE_FILES
    query = question or "Summarize the key information from the loaded files."

    print("=== Manual File Test ===")
    print("Accepted file types: .md, .txt")
    print("Input file list:")
    for file_path in files:
        print(f"  - {file_path}")

    docs = load_documents_from_files(files)
    if not docs:
        print("\nNo valid input files were loaded.")
        print("Create files matching the sample paths above, then rerun:")
        print("  python3 main.py")
        return 1

    print(f"\nLoaded {len(docs)} documents")
    for doc in docs:
        print(f"  - {doc.id}: {doc.metadata['source']}")

    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    print(f"\nEmbedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

    chunked_docs = build_chunked_documents(docs, strategy=DEFAULT_CHUNK_STRATEGY)
    store = EmbeddingStore(collection_name="manual_test_store", embedding_fn=embedder)
    store.add_documents(chunked_docs)

    print(
        f"\nStored {store.get_collection_size()} chunks in EmbeddingStore "
        f"using strategy='{DEFAULT_CHUNK_STRATEGY}'"
    )
    print("\n=== EmbeddingStore Search Test ===")
    print(f"Query: {query}")
    search_results = store.search(query, top_k=3)
    for index, result in enumerate(search_results, start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   content preview: {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent Test ===")
    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)
    print(f"Question: {query}")
    print("Agent answer:")
    print(agent.answer(query, top_k=3))
    return 0


def run_phase2_benchmark(strategy: str = DEFAULT_CHUNK_STRATEGY, top_k: int = 3) -> int:
    print("=== Phase 2 Benchmark ===")
    print(f"Strategy: {strategy}")
    print(f"Top-k: {top_k}")

    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    documents = load_documents_from_files(SAMPLE_FILES)
    chunked_documents = build_chunked_documents(documents, strategy=strategy)
    store = EmbeddingStore(collection_name=f"phase2_{strategy}", embedding_fn=embedder)
    store.add_documents(chunked_documents)

    print(f"Loaded {len(documents)} documents into {len(chunked_documents)} chunks")
    hit_count = 0

    for index, benchmark in enumerate(PHASE2_BENCHMARKS, start=1):
        query = benchmark["query"]
        expected_doc_id = benchmark["expected_doc_id"]
        metadata_filter = None
        if expected_doc_id == "nghidinh161-2026":
            metadata_filter = {"doc_type": "decree", "topic": "base_salary"}
            results = store.search_with_filter(query, top_k=top_k, metadata_filter=metadata_filter)
        else:
            results = store.search(query, top_k=top_k)

        hit = any(result["metadata"].get("doc_id") == expected_doc_id for result in results)
        if hit:
            hit_count += 1

        print(f"\n[{index}] Query: {query}")
        print(f"Expected doc: {expected_doc_id}")
        print(f"Hit in top-{top_k}: {'YES' if hit else 'NO'}")
        if metadata_filter:
            print(f"Filter used: {metadata_filter}")
        for result_rank, result in enumerate(results, start=1):
            preview = result["content"][:160].replace("\n", " ")
            print(
                f"  {result_rank}. score={result['score']:.3f} "
                f"doc_id={result['metadata'].get('doc_id')} "
                f"chunk={result['metadata'].get('chunk_index')}"
            )
            print(f"     preview: {preview}...")

    print(f"\nHit@{top_k}: {hit_count}/{len(PHASE2_BENCHMARKS)}")
    return 0


def run_all_phase2_benchmarks(top_k: int = 3) -> int:
    print("=== Phase 2 Benchmark: All Strategies ===")
    summary: list[tuple[str, int, int]] = []

    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    documents = load_documents_from_files(SAMPLE_FILES)

    for strategy, description in AVAILABLE_STRATEGIES.items():
        chunked_documents = build_chunked_documents(documents, strategy=strategy)
        store = EmbeddingStore(collection_name=f"phase2_{strategy}", embedding_fn=embedder)
        store.add_documents(chunked_documents)

        hit_count = 0
        for benchmark in PHASE2_BENCHMARKS:
            query = benchmark["query"]
            expected_doc_id = benchmark["expected_doc_id"]
            if expected_doc_id == "nghidinh161-2026":
                results = store.search_with_filter(
                    query,
                    top_k=top_k,
                    metadata_filter={"doc_type": "decree", "topic": "base_salary"},
                )
            else:
                results = store.search(query, top_k=top_k)
            if any(result["metadata"].get("doc_id") == expected_doc_id for result in results):
                hit_count += 1

        summary.append((strategy, len(chunked_documents), hit_count))
        print(
            f"{strategy}: {description} | "
            f"chunks={len(chunked_documents)} | Hit@{top_k}={hit_count}/{len(PHASE2_BENCHMARKS)}"
        )

    print("\n=== Summary ===")
    for strategy, chunk_count, hit_count in summary:
        print(f"- {strategy}: chunks={chunk_count}, Hit@{top_k}={hit_count}/{len(PHASE2_BENCHMARKS)}")

    return 0


def main() -> int:
    configure_stdout()
    args = sys.argv[1:]
    if args and args[0] == "--list-strategies":
        print("Available strategies:")
        for strategy, description in AVAILABLE_STRATEGIES.items():
            print(f"- {strategy}: {description}")
        return 0
    if args and args[0] == "--benchmark":
        strategy = args[1] if len(args) > 1 else DEFAULT_CHUNK_STRATEGY
        if strategy == "all":
            return run_all_phase2_benchmarks()
        return run_phase2_benchmark(strategy=strategy)

    question = " ".join(args).strip() if args else None
    return run_manual_demo(question=question)


if __name__ == "__main__":
    raise SystemExit(main())
