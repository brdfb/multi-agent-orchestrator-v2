"""
Embedding engine for semantic search with multilingual support.

Uses sentence-transformers with a lightweight multilingual model that supports
50+ languages including Turkish, English, Arabic, Chinese, etc.

Model: paraphrase-multilingual-MiniLM-L12-v2
- Size: ~420MB
- Dimensions: 384
- Languages: 50+
- Speed: ~2000 sentences/sec on CPU
"""

import numpy as np
from typing import List, Optional
import pickle


class EmbeddingEngine:
    """Generates and manages text embeddings for semantic search."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize embedding engine with lazy loading.

        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self._model = None  # Lazy loading

    @property
    def model(self):
        """Lazy load the model only when first needed."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                print(f"🔄 Loading embedding model: {self.model_name}...")
                self._model = SentenceTransformer(self.model_name)
                print(f"✅ Model loaded (embedding dim: {self._model.get_sentence_embedding_dimension()})")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load embedding model: {e}")

        return self._model

    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text in any supported language

        Returns:
            Numpy array of shape (384,) containing the embedding
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.model.get_sentence_embedding_dimension())

        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts (more efficient).

        Args:
            texts: List of input texts

        Returns:
            Numpy array of shape (N, 384) where N is number of texts
        """
        if not texts:
            return np.array([])

        # Filter empty texts
        texts = [t if t and t.strip() else " " for t in texts]

        # Generate embeddings in batch
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=len(texts) > 10)
        return embeddings

    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1 (1 = identical, 0 = orthogonal)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Clamp to [0, 1] range (numerical errors can cause slight overflow)
        return float(max(0.0, min(1.0, similarity)))

    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embedding vectors
            top_k: Number of top results to return

        Returns:
            List of (index, similarity_score) tuples, sorted by similarity descending
        """
        if not candidate_embeddings:
            return []

        # Calculate similarities
        similarities = [
            (idx, self.cosine_similarity(query_embedding, emb))
            for idx, emb in enumerate(candidate_embeddings)
        ]

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        return similarities[:top_k]

    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """
        Serialize embedding to bytes for database storage.

        Args:
            embedding: Numpy array embedding

        Returns:
            Pickled bytes representation
        """
        return pickle.dumps(embedding)

    @staticmethod
    def deserialize_embedding(data: bytes) -> np.ndarray:
        """
        Deserialize embedding from database bytes.

        Args:
            data: Pickled bytes from database

        Returns:
            Numpy array embedding
        """
        return pickle.loads(data)


# Global singleton instance (lazy loaded)
_embedding_engine: Optional[EmbeddingEngine] = None


def get_embedding_engine() -> EmbeddingEngine:
    """Get or create the global embedding engine instance."""
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine
