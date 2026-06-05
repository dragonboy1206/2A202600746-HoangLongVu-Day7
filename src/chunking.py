from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])(?:\s+|\n+)", text.strip())
            if sentence.strip()
        ]
        if not sentences:
            return [text.strip()]

        chunks: list[str] = []
        for index in range(0, len(sentences), self.max_sentences_per_chunk):
            chunk = " ".join(sentences[index : index + self.max_sentences_per_chunk]).strip()
            if chunk:
                chunks.append(chunk)
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return [chunk for chunk in self._split(text, self.separators) if chunk]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]
        if not remaining_separators:
            return FixedSizeChunker(chunk_size=self.chunk_size, overlap=0).chunk(current_text)

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        if separator == "":
            return FixedSizeChunker(chunk_size=self.chunk_size, overlap=0).chunk(current_text)

        pieces = current_text.split(separator)
        if len(pieces) == 1:
            return self._split(current_text, next_separators)

        chunks: list[str] = []
        buffer = ""

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            candidate = piece if not buffer else f"{buffer}{separator}{piece}"
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.extend(self._split(buffer, next_separators))
                buffer = ""

            if len(piece) <= self.chunk_size:
                buffer = piece
            else:
                chunks.extend(self._split(piece, next_separators))

        if buffer:
            chunks.extend(self._split(buffer, next_separators))

        return chunks


class LegalChunker:
    """
    Split legal documents by structural markers such as chapter/article headings.

    This strategy works well for Vietnamese legal texts that use markers like:
        - "Chương I"
        - "Điều 1."
        - "Khoản 1."

    If no useful legal markers are found, it falls back to RecursiveChunker.
    """

    SECTION_PATTERN = re.compile(
        r"(?=(?:Chương|Chuong)\s+[IVXLC0-9]+)|(?=(?:Điều|Dieu)\s+\d+[\.\:])|(?=(?:Khoản|Khoan)\s+\d+[\.\:])"
    )

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        parts = [part.strip() for part in self.SECTION_PATTERN.split(text.strip()) if part.strip()]
        if len(parts) <= 1:
            return self._fallback.chunk(text)

        chunks: list[str] = []
        buffer = ""

        for part in parts:
            candidate = part if not buffer else f"{buffer}\n\n{part}"
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.extend(self._fallback.chunk(buffer))
                buffer = ""

            if len(part) <= self.chunk_size:
                buffer = part
            else:
                chunks.extend(self._fallback.chunk(part))

        if buffer:
            chunks.extend(self._fallback.chunk(buffer))

        return [chunk for chunk in chunks if chunk.strip()]


class HybridLegalChunker:
    """
    Split legal documents in two stages:
        1. Split by legal section markers when possible.
        2. Refine oversized sections with SentenceChunker or RecursiveChunker.

    This strategy is useful when legal sections are meaningful, but some sections
    are still too long and need finer-grained sentence-level splitting.
    """

    SECTION_PATTERN = LegalChunker.SECTION_PATTERN

    def __init__(self, chunk_size: int = 500, max_sentences_per_chunk: int = 2) -> None:
        self.chunk_size = chunk_size
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)
        self._sentence_chunker = SentenceChunker(max_sentences_per_chunk=self.max_sentences_per_chunk)
        self._recursive_chunker = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections = [section.strip() for section in self.SECTION_PATTERN.split(text.strip()) if section.strip()]
        if len(sections) <= 1:
            return self._recursive_chunker.chunk(text)

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            sentence_chunks = self._sentence_chunker.chunk(section)
            for sentence_chunk in sentence_chunks:
                if len(sentence_chunk) <= self.chunk_size:
                    chunks.append(sentence_chunk)
                else:
                    chunks.extend(self._recursive_chunker.chunk(sentence_chunk))

        return [chunk for chunk in chunks if chunk.strip()]


class EnsembleChunker:
    """
    Combine multiple chunking strategies and deduplicate the results.

    The goal is to keep:
        - sentence-level semantic clarity
        - legal-structure boundaries
        - recursive fallback coverage
    """

    def __init__(self, chunk_size: int = 500, max_sentences_per_chunk: int = 2) -> None:
        self.chunk_size = chunk_size
        self._chunkers = [
            SentenceChunker(max_sentences_per_chunk=max_sentences_per_chunk),
            LegalChunker(chunk_size=chunk_size),
            RecursiveChunker(chunk_size=chunk_size),
        ]

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        seen: set[str] = set()
        combined: list[str] = []

        for chunker in self._chunkers:
            for chunk in chunker.chunk(text):
                normalized = re.sub(r"\s+", " ", chunk).strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                combined.append(normalized)

        return combined


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    if not vec_a or not vec_b:
        return 0.0

    norm_a = math.sqrt(sum(value * value for value in vec_a))
    norm_b = math.sqrt(sum(value * value for value in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=min(50, max(0, chunk_size // 10))),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        comparison: dict[str, dict[str, object]] = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = (sum(len(chunk) for chunk in chunks) / count) if count else 0.0
            comparison[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return comparison
