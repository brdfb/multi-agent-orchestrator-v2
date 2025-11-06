"""
Smoke tests for semantic search functionality.

These are minimal tests for regression protection, not comprehensive coverage.
Run with: pytest tests/test_semantic_search.py -v
"""
import pytest
import tempfile
from pathlib import Path
from core.embedding_engine import get_embedding_engine, EmbeddingEngine
from core.memory_engine import MemoryEngine
from core.memory_backend import SQLiteBackend


@pytest.fixture
def temp_memory():
    """Fixture for creating a fresh MemoryEngine with temporary database."""
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    # Create fresh memory engine with temp backend
    memory = MemoryEngine()
    memory.backend = SQLiteBackend(tmp_path)
    memory._initialized = True

    yield memory

    # Cleanup
    if tmp_path.exists():
        tmp_path.unlink()


def test_embedding_engine_loads():
    """Verify embedding engine can be initialized without crash."""
    engine = get_embedding_engine()
    assert engine is not None
    assert engine.model_name == "paraphrase-multilingual-MiniLM-L12-v2"


def test_embedding_generation():
    """Verify embeddings can be generated for text."""
    engine = get_embedding_engine()

    # Test English
    embedding_en = engine.encode("Hello world")
    assert embedding_en is not None
    assert len(embedding_en) == 384  # Model dimension

    # Test Turkish
    embedding_tr = engine.encode("Merhaba dünya")
    assert embedding_tr is not None
    assert len(embedding_tr) == 384


def test_cosine_similarity_basic():
    """Verify cosine similarity calculation works."""
    engine = get_embedding_engine()

    # Similar sentences should have high similarity
    emb1 = engine.encode("Kubernetes deployment with Helm chart")
    emb2 = engine.encode("Helm chart for Kubernetes deployment")
    similarity = engine.cosine_similarity(emb1, emb2)

    assert 0.0 <= similarity <= 1.0
    assert similarity > 0.7  # Should be similar


def test_embedding_serialization():
    """Verify embeddings can be serialized and deserialized."""
    engine = get_embedding_engine()

    original = engine.encode("Test text")
    serialized = EmbeddingEngine.serialize_embedding(original)
    deserialized = EmbeddingEngine.deserialize_embedding(serialized)

    assert len(deserialized) == len(original)
    assert (deserialized == original).all()


def test_semantic_search_basic(temp_memory):
    """
    Smoke test for semantic search integration.

    This tests the basic happy path:
    1. Store a conversation
    2. Search with semantic strategy
    3. Verify context is found
    """
    # Store a test conversation
    conv_id = temp_memory.store_conversation(
        prompt="Create a Kubernetes Helm chart with Redis",
        response="Here's a Helm chart structure...",
        agent="builder",
        model="test-model",
        provider="test",
        generate_embedding=True
    )

    assert conv_id > 0

    # Search with semantic strategy
    context = temp_memory.get_context_for_prompt(
        prompt="Helm chart for Kubernetes",
        strategy="semantic",
        max_tokens=500,
        min_relevance=0.3
    )

    # Should find the conversation we just stored
    assert context != ""
    assert "Redis" in context or "Helm" in context


def test_turkish_semantic_search(temp_memory):
    """
    Test semantic search with Turkish language prompts.

    This was the original use case that motivated semantic search.
    """
    # Store Turkish conversation
    conv_id = temp_memory.store_conversation(
        prompt="Kubernetes deployment için Helm chart oluştur",
        response="İşte Helm chart yapısı...",
        agent="builder",
        model="test-model",
        provider="test",
        generate_embedding=True
    )

    # Search with Turkish prompt (different form: "chart" vs "chart'a")
    context = temp_memory.get_context_for_prompt(
        prompt="Önceki Helm chart'a eklemeler yap",  # Different Turkish suffix
        strategy="semantic",
        max_tokens=500,
        min_relevance=0.3
    )

    # Semantic search should find it despite morphological differences
    assert context != ""


def test_hybrid_strategy(temp_memory):
    """Verify hybrid strategy doesn't crash."""
    conv_id = temp_memory.store_conversation(
        prompt="Test hybrid search",
        response="Response content",
        agent="builder",
        model="test",
        provider="test",
        generate_embedding=True
    )

    # Hybrid: 70% semantic + 30% keyword
    context = temp_memory.get_context_for_prompt(
        prompt="hybrid search test",
        strategy="hybrid",
        max_tokens=500
    )

    # Should not crash
    assert context is not None


def test_empty_text_handling():
    """Verify graceful handling of edge cases."""
    engine = get_embedding_engine()

    # Empty string
    embedding = engine.encode("")
    assert embedding is not None
    assert len(embedding) == 384  # Returns zero vector

    # Whitespace only
    embedding = engine.encode("   ")
    assert embedding is not None
