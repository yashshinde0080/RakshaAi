"""
Document chunker.
Splits documents into overlapping chunks for embedding.
No naive split. Proper boundary detection.
"""

import re
import uuid
import logging
from typing import List

from app.schemas.vector_schemas import TextChunk

logger = logging.getLogger("sovereign.vectorstore.chunker")


class DocumentChunker:
    """
    Split text into overlapping chunks.
    Respects sentence boundaries when possible.
    """

    def __init__(self, chunk_size: int = 512,
                 chunk_overlap: int = 64,
                 max_chunks: int = 10000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunks = max_chunks

        # Sentence boundary pattern
        self._sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])'
        )

    def chunk_text(self, text: str,
                   document_id: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Strategy:
        1. Try to split on sentence boundaries.
        2. If chunk too large, fall back to character split.
        3. Always maintain overlap.
        """
        if not text or not text.strip():
            return []

        # Clean text
        text = self._clean_text(text)

        # Split into sentences first
        sentences = self._split_sentences(text)

        # Build chunks from sentences
        chunks = self._build_chunks(sentences, document_id, text)

        if len(chunks) > self.max_chunks:
            logger.warning(
                f"Document {document_id}: {len(chunks)} chunks exceeds "
                f"max {self.max_chunks}. Truncating."
            )
            chunks = chunks[:self.max_chunks]

        logger.info(
            f"Document {document_id}: {len(chunks)} chunks created"
        )
        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = self._sentence_pattern.split(text)
        # Filter empty
        return [s.strip() for s in sentences if s.strip()]

    def _build_chunks(self, sentences: List[str],
                      document_id: str,
                      original_text: str) -> List[TextChunk]:
        """
        Build chunks from sentences with overlap.
        """
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        char_position = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If single sentence exceeds chunk size, force split it
            if sentence_length > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    start_char = original_text.find(
                        current_chunk[0], max(0, char_position - 100)
                    )
                    if start_char == -1:
                        start_char = char_position

                    chunks.append(TextChunk(
                        chunk_id=self._generate_chunk_id(
                            document_id, chunk_index
                        ),
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                        token_count=self._estimate_tokens(chunk_text)
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0

                # Force split long sentence
                sub_chunks = self._force_split(
                    sentence, document_id, chunk_index, char_position
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                char_position += sentence_length
                continue

            # Check if adding sentence would exceed chunk size
            if current_length + sentence_length + 1 > self.chunk_size:
                # Emit current chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    start_char = original_text.find(
                        current_chunk[0], max(0, char_position - 100)
                    )
                    if start_char == -1:
                        start_char = char_position

                    chunks.append(TextChunk(
                        chunk_id=self._generate_chunk_id(
                            document_id, chunk_index
                        ),
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                        token_count=self._estimate_tokens(chunk_text)
                    ))
                    chunk_index += 1

                    # Overlap: keep last few sentences
                    overlap_chars = 0
                    overlap_sentences = []
                    for s in reversed(current_chunk):
                        if overlap_chars + len(s) <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_chars += len(s) + 1
                        else:
                            break

                    current_chunk = overlap_sentences
                    current_length = sum(
                        len(s) + 1 for s in current_chunk
                    )

            current_chunk.append(sentence)
            current_length += sentence_length + 1
            char_position += sentence_length + 1

        # Flush remaining
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            start_char = max(0, len(original_text) - len(chunk_text))
            chunks.append(TextChunk(
                chunk_id=self._generate_chunk_id(
                    document_id, chunk_index
                ),
                document_id=document_id,
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + len(chunk_text),
                token_count=self._estimate_tokens(chunk_text)
            ))

        return chunks

    def _force_split(self, text: str, document_id: str,
                     start_index: int,
                     char_offset: int) -> List[TextChunk]:
        """Force split text that exceeds chunk size."""
        chunks = []
        pos = 0
        idx = start_index

        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))

            # Try to find a word boundary
            if end < len(text):
                space_pos = text.rfind(' ', pos, end)
                if space_pos > pos:
                    end = space_pos

            chunk_content = text[pos:end].strip()
            if chunk_content:
                chunks.append(TextChunk(
                    chunk_id=self._generate_chunk_id(document_id, idx),
                    document_id=document_id,
                    content=chunk_content,
                    chunk_index=idx,
                    start_char=char_offset + pos,
                    end_char=char_offset + end,
                    token_count=self._estimate_tokens(chunk_content)
                ))
                idx += 1

            # Move with overlap
            pos = max(pos + 1, end - self.chunk_overlap)

        return chunks

    def _generate_chunk_id(self, document_id: str,
                           chunk_index: int) -> str:
        """Generate deterministic chunk ID."""
        return f"{document_id}_chunk_{chunk_index:06d}"

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation.
        Average English: ~4 chars per token.
        Not perfect. Good enough for budget estimation.
        """
        return max(1, len(text) // 4)