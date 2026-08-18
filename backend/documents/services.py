import os
import re
import math
import logging
import threading
import pypdf
from django.conf import settings
from .models import Document, DocumentChunk

logger = logging.getLogger(__name__)

# Module-level thread-safe singleton for fastembed model
_EMBEDDING_MODEL = None
_EMBEDDING_LOCK = threading.Lock()

BROAD_QUERY_PATTERNS = [
    r"\bwhat\s+is\s+(this|the)\s+(document|book|pdf|file)\s+about\b",
    r"\bwhat\s+is\s+about\b",
    r"\bkey\s+points?\b",
    r"\bmain\s+points?\b",
    r"\bmain\s+topics?\b",
    r"\bsummar(ize|y)\b",
    r"\boverview\b",
    r"\bwhat\s+does\s+this\s+(document|book|pdf|file)\s+cover\b",
    r"\bwhat\s+topics?\s+are\s+covered\b",
    r"\bbrief\s+summary\b",
    r"\bgeneral\s+summary\b",
    r"\boutline\b",
    r"\btable\s+of\s+contents\b",
]


def is_broad_query(query_text: str) -> bool:
    """
    Determines whether a user query is a broad/summary document question.
    """
    if not query_text:
        return False
    q_lower = query_text.lower().strip()
    for pattern in BROAD_QUERY_PATTERNS:
        if re.search(pattern, q_lower):
            return True
    return False


def clean_query_text(query_text: str, filename: str = None) -> str:
    """
    Removes filename references (e.g. book.pdf, searching 8.pdf) from the embedding query text
    without removing meaningful words from the actual user question.
    """
    if not query_text:
        return ""
    cleaned = query_text

    # 1. If filename is provided, remove exact filename match (case-insensitive)
    if filename:
        pattern = re.escape(filename)
        cleaned = re.sub(pattern, "this document", cleaned, flags=re.IGNORECASE)

    # 2. General regex for filenames like 'searching 8.pdf', 'document.txt', etc.
    cleaned = re.sub(r'\b[\w\s-]+\.(pdf|txt|docx?)\b', 'this document', cleaned, flags=re.IGNORECASE)

    # Clean up double spaces or trailing punctuation artifacts
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else query_text


def get_embedding_model():
    """
    Thread-safe lazy initialization singleton for fastembed TextEmbedding model.
    Configured with single-threaded ONNX execution (threads=1) to prevent memory spikes on Render.
    """
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_MODEL is None:
                try:
                    from fastembed import TextEmbedding
                    hf_token = os.getenv('HF_TOKEN') or getattr(settings, 'HF_TOKEN', None)
                    logger.info(
                        f"Initializing FastEmbed TextEmbedding (model='BAAI/bge-small-en-v1.5', threads=1, "
                        f"hf_token_present={bool(hf_token)})..."
                    )

                    # Initialize single-threaded FastEmbed model (384 dimensions)
                    _EMBEDDING_MODEL = TextEmbedding(
                        model_name="BAAI/bge-small-en-v1.5",
                        threads=1
                    )
                    logger.info("FastEmbed TextEmbedding model (BAAI/bge-small-en-v1.5) initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize FastEmbed model: {e}")
                    raise RuntimeError(f"Embedding model initialization failed: {e}")
    return _EMBEDDING_MODEL


class DocumentService:
    """
    Service responsible for document text extraction (PDF/TXT), chunking,
    local vector embedding generation via fastembed, and Python Cosine Similarity retrieval.
    """

    @staticmethod
    def extract_text(file_obj, filename: str) -> str:
        """
        Extracts plain text from uploaded PDF or TXT file objects.
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == '.txt':
            try:
                content = file_obj.read()
                if isinstance(content, bytes):
                    text = content.decode('utf-8', errors='ignore')
                else:
                    text = str(content)
            except Exception as e:
                logger.error(f"Error reading TXT file {filename}: {e}")
                raise ValueError("Failed to read text file.")

        elif ext == '.pdf':
            try:
                reader = pypdf.PdfReader(file_obj)
                extracted_pages = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text)
                text = "\n".join(extracted_pages)
            except Exception as e:
                logger.error(f"Error parsing PDF file {filename}: {e}")
                raise ValueError("Failed to parse PDF document.")

        else:
            raise ValueError("Unsupported file format. Please upload a PDF or TXT file.")

        text = text.strip()
        if not text:
            raise ValueError("This PDF does not contain extractable text. Please upload a text-based PDF.")

        return text

    @staticmethod
    def generate_embeddings(texts: list) -> list:
        """
        Generates dense 384-dimensional vector embeddings for a list of text strings using fastembed.
        Uses batch_size=16 for memory efficiency.
        """
        if not texts:
            return []
        model = get_embedding_model()
        # model.embed returns a generator of numpy arrays; batch_size keeps memory footprint steady
        embeddings_gen = model.embed(texts, batch_size=16)
        return [vec.tolist() for vec in embeddings_gen]

    @staticmethod
    def cosine_similarity(vec1: list, vec2: list) -> float:
        """
        Computes exact mathematical cosine similarity between two vector lists.
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @classmethod
    def create_chunks(cls, document: Document, text: str, chunk_size_words: int = 400, overlap_words: int = 50):
        """
        Splits text into overlapping chunks, streams vector embeddings via fastembed generator,
        and bulk stores DocumentChunk DB records in memory-safe batches.
        """
        words = text.split()
        if not words:
            return

        chunk_texts = []
        step = max(1, chunk_size_words - overlap_words)

        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size_words]
            chunk_text = " ".join(chunk_words)
            chunk_texts.append(chunk_text)

            if i + chunk_size_words >= len(words):
                break

        if not chunk_texts:
            return

        model = get_embedding_model()

        # Stream embedding generator with batch_size=16 for steady low memory usage
        embeddings_gen = model.embed(chunk_texts, batch_size=16)

        batch_objects = []
        batch_limit = 32

        for idx, (chunk_text, vec) in enumerate(zip(chunk_texts, embeddings_gen)):
            batch_objects.append(DocumentChunk(
                document=document,
                content=chunk_text,
                chunk_index=idx,
                embedding=vec.tolist()
            ))

            if len(batch_objects) >= batch_limit:
                DocumentChunk.objects.bulk_create(batch_objects)
                batch_objects.clear()

        if batch_objects:
            DocumentChunk.objects.bulk_create(batch_objects)
            batch_objects.clear()

    @classmethod
    def clean_query_text(cls, query_text: str, filename: str = None) -> str:
        return clean_query_text(query_text, filename)

    @classmethod
    def is_broad_query(cls, query_text: str) -> bool:
        return is_broad_query(query_text)

    @classmethod
    def get_relevant_chunks(cls, document: Document, query_text: str, top_k: int = None) -> list:
        """
        Generates query vector embedding, computes Cosine Similarity against DocumentChunks,
        and returns relevant chunk contents.
        - Broad/summary queries: Retrieves 6-8 representative chunks distributed across document.
        - Specific queries: Retrieves top 4 cosine similarity chunks.
        - Final chunks are sorted by chunk_index ascending before returning to preserve document order.
        """
        chunks = list(document.chunks.all().order_by('chunk_index'))
        if not chunks:
            return []

        total_chunks = len(chunks)
        is_broad = is_broad_query(query_text)

        # 1. Clean query text (remove filename references) for embedding vector generation
        cleaned_query = cls.clean_query_text(query_text, document.filename)

        # 2. Generate 384-dimensional query vector embedding
        query_embeddings = cls.generate_embeddings([cleaned_query])
        if not query_embeddings:
            if is_broad or (top_k and top_k >= 6):
                return [c.content for c in chunks[:min(8, total_chunks)]]
            return [c.content for c in chunks[:min(4, total_chunks)]]

        query_vec = query_embeddings[0]

        # 3. Compute Cosine Similarity for each chunk
        scored_chunks = []
        for chunk in chunks:
            chunk_vec = chunk.embedding
            sim_score = cls.cosine_similarity(query_vec, chunk_vec) if chunk_vec else 0.0
            scored_chunks.append((sim_score, chunk))

        selected_chunks = []

        if is_broad:
            if total_chunks <= 6:
                selected_chunks = chunks
            else:
                target_k = 6
                selected_set = set()
                segment_size = total_chunks / target_k
                for i in range(target_k):
                    start_idx = int(i * segment_size)
                    end_idx = int((i + 1) * segment_size) if i < target_k - 1 else total_chunks
                    segment_scored = scored_chunks[start_idx:end_idx]
                    if segment_scored:
                        best_in_segment = max(segment_scored, key=lambda item: item[0])[1]
                        selected_set.add(best_in_segment)

                selected_chunks = list(selected_set)

                if len(selected_chunks) < target_k:
                    scored_chunks_sorted = sorted(scored_chunks, key=lambda item: item[0], reverse=True)
                    for item in scored_chunks_sorted:
                        if item[1] not in selected_set:
                            selected_chunks.append(item[1])
                            if len(selected_chunks) >= target_k:
                                break
        else:
            k = top_k if top_k is not None else 4
            scored_chunks_sorted = sorted(scored_chunks, key=lambda item: item[0], reverse=True)
            selected_chunks = [item[1] for item in scored_chunks_sorted[:k]]

        # Sort final retrieved chunks by chunk_index ascending to follow document reading order
        selected_chunks.sort(key=lambda c: c.chunk_index)

        return [c.content for c in selected_chunks]

