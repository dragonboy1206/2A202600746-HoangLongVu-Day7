from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            client = chromadb.Client()
            self._collection = client.get_or_create_collection(name=collection_name)
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        metadata = dict(doc.metadata)
        metadata.setdefault("doc_id", doc.id)
        return {
            "id": f"{doc.id}_{self._next_index}",
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }

    def _normalize_text(self, text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text.lower())
        without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        return without_marks

    def _tokenize(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        return {
            token
            for token in re.findall(r"\w+", normalized)
            if len(token) >= 2 and not token.isdigit()
        }

    def _keyword_overlap_score(self, query: str, content: str, metadata: dict[str, Any]) -> float:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0

        content_tokens = self._tokenize(content)
        title_tokens = self._tokenize(str(metadata.get("title", "")))
        topic_tokens = self._tokenize(str(metadata.get("topic", "")))

        overlap = len(query_tokens & content_tokens) / len(query_tokens)
        title_overlap = len(query_tokens & title_tokens) / len(query_tokens)
        topic_overlap = len(query_tokens & topic_tokens) / len(query_tokens)
        return overlap + (0.4 * title_overlap) + (0.2 * topic_overlap)

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        scored: list[dict[str, Any]] = []
        for record in records:
            vector_score = _dot(query_embedding, record["embedding"])
            lexical_score = self._keyword_overlap_score(query, record["content"], record["metadata"])
            score = (0.45 * vector_score) + (0.55 * lexical_score)
            scored.append(
                {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": record["metadata"],
                    "score": score,
                    "vector_score": vector_score,
                    "lexical_score": lexical_score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        records = []
        for doc in docs:
            record = self._make_record(doc)
            self._next_index += 1
            records.append(record)

        if self._use_chroma and self._collection is not None:
            self._collection.add(
                ids=[record["id"] for record in records],
                documents=[record["content"] for record in records],
                embeddings=[record["embedding"] for record in records],
                metadatas=[record["metadata"] for record in records],
            )

        self._store.extend(records)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered_records = [
            record
            for record in self._store
            if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, filtered_records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        original_size = len(self._store)
        records_to_delete = [record for record in self._store if record["metadata"].get("doc_id") == doc_id]
        if not records_to_delete:
            return False

        self._store = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]

        if self._use_chroma and self._collection is not None:
            self._collection.delete(ids=[record["id"] for record in records_to_delete])

        return len(self._store) < original_size
