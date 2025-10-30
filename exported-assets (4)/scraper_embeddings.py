"""
Embedding functionality for segments.

Uses sentence-transformers to generate embeddings for text segments.
"""

import logging
import numpy as np
from typing import List, Optional
import sqlite3

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. "
        "Run: pip install sentence-transformers"
    )

# Default model - same as commonly used in embedding applications
DEFAULT_MODEL = 'all-MiniLM-L6-v2'


class EmbeddingGenerator:
    """Generate embeddings for text segments."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.model = None

    def _load_model(self):
        """Lazy load the model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings

        Returns:
            Array of embeddings (shape: [len(texts), embedding_dim])
        """
        self._load_model()

        # Generate embeddings with normalization
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,
        )

        return embeddings

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]


def embed_segments(
    conn: sqlite3.Connection,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
):
    """
    Generate embeddings for all segments without embeddings.

    Args:
        conn: Database connection
        model_name: Name of sentence-transformers model
        batch_size: Batch size for embedding generation
    """
    from .db import get_segments_without_embeddings, update_segment_embedding

    # Get segments without embeddings
    segments = get_segments_without_embeddings(conn)

    if not segments:
        logger.info("No segments need embeddings")
        return

    logger.info(f"Generating embeddings for {len(segments)} segments")

    # Initialize generator
    generator = EmbeddingGenerator(model_name)

    # Process in batches
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i+batch_size]
        texts = [seg['text'] for seg in batch]

        # Generate embeddings
        embeddings = generator.embed_texts(texts)

        # Store in database
        for seg, embedding in zip(batch, embeddings):
            # Convert to bytes for storage
            embedding_bytes = embedding.astype(np.float32).tobytes()
            update_segment_embedding(conn, seg['id'], embedding_bytes)

        logger.info(f"Embedded {min(i+batch_size, len(segments))}/{len(segments)} segments")

    logger.info("Embedding generation complete")


def index_segments(
    conn: sqlite3.Connection,
    source_id: int,
    segments: List,
    generate_embeddings: bool = True,
    model_name: str = DEFAULT_MODEL,
):
    """
    Index segments into database with optional embeddings.

    Args:
        conn: Database connection
        source_id: Source ID
        segments: List of Segment objects
        generate_embeddings: Whether to generate embeddings
        model_name: Embedding model name
    """
    from .db import insert_segments

    # Insert segments
    segment_ids = insert_segments(conn, source_id, segments)

    logger.info(f"Inserted {len(segment_ids)} segments")

    # Generate embeddings if requested
    if generate_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE:
        embed_segments(conn, model_name)
