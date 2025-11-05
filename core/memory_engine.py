"""Memory engine for persistent conversation storage and retrieval."""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from core.memory_backend import SQLiteBackend
from core.embedding_engine import get_embedding_engine, EmbeddingEngine


class MemoryEngine:
    """
    Singleton memory engine for managing conversation persistence.

    Provides high-level interface for storing, retrieving, and searching conversations.
    Uses SQLite backend by default.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize memory engine (only once)."""
        if not self._initialized:
            self.backend = SQLiteBackend()
            self.enabled = True  # Can be disabled via config
            self._embedding_engine: Optional[EmbeddingEngine] = None  # Lazy load
            self._initialized = True

    @property
    def embedding_engine(self) -> EmbeddingEngine:
        """Lazy load embedding engine only when needed."""
        if self._embedding_engine is None:
            self._embedding_engine = get_embedding_engine()
        return self._embedding_engine

    def store_conversation(
        self,
        prompt: str,
        response: str,
        agent: str,
        model: str,
        provider: str,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: bool = True,
    ) -> int:
        """
        Store conversation to memory with optional embedding generation.

        Args:
            prompt: User prompt
            response: Agent response
            agent: Agent name (builder, critic, closer, etc.)
            model: Model identifier
            provider: Provider name (openai, anthropic, google)
            metadata: Additional metadata (tokens, cost, duration, etc.)
            generate_embedding: Whether to generate and store embedding

        Returns:
            Conversation ID
        """
        if not self.enabled:
            return -1

        # Build conversation record
        conversation = {
            "prompt": prompt,
            "response": response,
            "agent": agent,
            "model": model,
            "provider": provider,
        }

        # Merge metadata
        if metadata:
            conversation.update(metadata)

        # Generate embedding if requested
        if generate_embedding:
            try:
                # Combine prompt + first 200 chars of response for embedding
                text_for_embedding = f"{prompt}\n{response[:200]}"
                embedding = self.embedding_engine.encode(text_for_embedding)
                conversation["embedding"] = EmbeddingEngine.serialize_embedding(embedding)
            except Exception:
                # If embedding fails, continue without it (graceful degradation)
                pass

        # Store to backend
        return self.backend.store(conversation)

    def get_recent_conversations(
        self, limit: int = 10, agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations.

        Args:
            limit: Maximum number of conversations
            agent: Filter by agent (optional)

        Returns:
            List of conversation dictionaries
        """
        if not self.enabled:
            return []

        return self.backend.get_recent(limit=limit, agent=agent)

    def search_conversations(
        self,
        query: Optional[str] = None,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations with filters.

        Args:
            query: Keyword search (in prompt/response)
            agent: Filter by agent
            model: Filter by model
            from_date: From date (ISO format)
            to_date: To date (ISO format)
            session_id: Filter by session
            limit: Max results

        Returns:
            List of matching conversations
        """
        if not self.enabled:
            return []

        return self.backend.search(
            query=query,
            agent=agent,
            model=model,
            from_date=from_date,
            to_date=to_date,
            session_id=session_id,
            limit=limit,
        )

    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dict or None
        """
        if not self.enabled:
            return None

        return self.backend.get_by_id(conversation_id)

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted
        """
        if not self.enabled:
            return False

        return self.backend.delete(conversation_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Stats dict with counts, tokens, costs
        """
        if not self.enabled:
            return {
                "total_conversations": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "by_agent": {},
                "by_model": {},
            }

        return self.backend.get_stats()

    def cleanup_old_conversations(self, days: int = 90) -> int:
        """
        Delete conversations older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of conversations deleted
        """
        if not self.enabled:
            return 0

        return self.backend.cleanup(days)

    def get_context_for_prompt(
        self,
        prompt: str,
        *,
        strategy: str = "keywords",
        max_tokens: int = 500,
        min_relevance: float = 0.25,
        time_decay_hours: int = 168,
        exclude_current_session: bool = True,
        agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Get relevant context from past conversations for a prompt.

        Supports multiple retrieval strategies:
        - keywords: Simple keyword matching (fast, multilingual-friendly)
        - semantic: Embedding-based semantic similarity (slow first time, accurate)
        - hybrid: Combination of both (weighted 70% semantic + 30% keywords)

        Args:
            prompt: Current user prompt
            strategy: Retrieval strategy ("keywords", "semantic", or "hybrid")
            max_tokens: Maximum tokens for context
            min_relevance: Minimum relevance score threshold (0-1)
            time_decay_hours: Time decay factor in hours (0 = no decay)
            exclude_current_session: Exclude conversations from current session
            agent: Filter by agent (None = all agents)
            session_id: Current session ID (for exclusion)

        Returns:
            Formatted context string
        """
        if not self.enabled:
            return ""

        # Query candidates from backend
        exclude_session = session_id if exclude_current_session else None
        candidates = self.backend.query_candidates(
            agent=agent, exclude_session_id=exclude_session, limit=500
        )

        if not candidates:
            return ""

        # Score candidates based on strategy
        if strategy == "semantic":
            scored = self._score_semantic(prompt, candidates, time_decay_hours)
        elif strategy == "hybrid":
            scored = self._score_hybrid(prompt, candidates, time_decay_hours)
        else:  # Default: keywords
            query_tokens = self._extract_keywords(prompt)
            scored = []
            for rec in candidates:
                score = self._score_record(
                    rec, query_tokens, time_decay_hours=time_decay_hours
                )
                if score >= min_relevance:
                    rec["_score"] = score
                    rec["_est_tokens"] = self._estimate_tokens(rec)
                    scored.append(rec)

        # Filter by min relevance
        scored = [r for r in scored if r.get("_score", 0) >= min_relevance]

        if not scored:
            return ""

        # Sort by score DESC, then timestamp DESC
        scored.sort(
            key=lambda r: (
                -r["_score"],
                -self._parse_timestamp(r["timestamp"]).timestamp(),
            )
        )

        # Budget selection
        picked = []
        budget = max_tokens
        for r in scored:
            if r["_est_tokens"] <= budget:
                picked.append(r)
                budget -= r["_est_tokens"]

        if not picked:
            return ""

        return self._format_context(picked)

    def _extract_keywords(self, text: str, min_length: int = 3) -> Set[str]:
        """
        Extract keywords from text (simple word extraction).

        Args:
            text: Input text
            min_length: Minimum word length

        Returns:
            Set of keywords
        """
        # Simple approach: split by space, filter short words and common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        words = text.lower().split()
        keywords = {
            w.strip(".,!?;:")
            for w in words
            if len(w) >= min_length and w.lower() not in stop_words
        }

        return keywords

    def _score_record(
        self, rec: Dict[str, Any], query_tokens: Set[str], *, time_decay_hours: int
    ) -> float:
        """
        Calculate relevance score for a conversation record.

        Score = keyword_overlap * exp(-age_hours / decay_hours)

        Args:
            rec: Conversation record
            query_tokens: Set of query keywords
            time_decay_hours: Time decay factor (0 = no decay)

        Returns:
            Relevance score (0-1)
        """
        # Keyword overlap scoring
        if not query_tokens:
            kw_score = 0.0
        else:
            doc_tokens = self._extract_keywords(rec["prompt"] + " " + rec["response"])
            overlap = len(query_tokens & doc_tokens)
            kw_score = overlap / max(1, len(query_tokens))

        # Time decay
        if time_decay_hours:
            age_hours = max(
                0.0,
                (
                    datetime.now(timezone.utc) - self._parse_timestamp(rec["timestamp"])
                ).total_seconds()
                / 3600,
            )
            decay = math.exp(-age_hours / float(time_decay_hours))
        else:
            decay = 1.0

        return kw_score * decay

    def _estimate_tokens(self, rec: Dict[str, Any]) -> int:
        """
        Estimate token count for a conversation record.

        Args:
            rec: Conversation record

        Returns:
            Estimated token count
        """
        # Simple heuristic: 4 chars ≈ 1 token
        # Format: "[Past conversation]\nQ: {prompt}\nA: {response}"
        text = f"[Past conversation]\nQ: {rec['prompt']}\nA: {rec['response']}"
        return len(text) // 4

    def _format_context(self, conversations: List[Dict[str, Any]]) -> str:
        """
        Format conversation records into context string.

        Args:
            conversations: List of conversation records (already scored/filtered)

        Returns:
            Formatted context string
        """
        if not conversations:
            return ""

        context_parts = []
        for conv in conversations:
            # Format: [Past conversation (score: X.XX)]
            score = conv.get("_score", 0.0)
            context_parts.append(
                f"[Past conversation (relevance: {score:.2f})]\n"
                f"Q: {conv['prompt']}\n"
                f"A: {conv['response']}"
            )

        return "\n\n".join(context_parts)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime object.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            datetime object
        """
        # Handle both with and without microseconds
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            # Fallback: try without timezone
            return datetime.fromisoformat(timestamp_str.split("+")[0].split("Z")[0])

    def enable(self):
        """Enable memory system."""
        self.enabled = True

    def disable(self):
        """Disable memory system."""
        self.enabled = False

    def _score_semantic(
        self,
        prompt: str,
        candidates: List[Dict[str, Any]],
        time_decay_hours: int,
    ) -> List[Dict[str, Any]]:
        """
        Score candidates using semantic similarity (embedding-based).

        Args:
            prompt: Query prompt
            candidates: Candidate conversation records
            time_decay_hours: Time decay factor

        Returns:
            List of scored records with _score and _est_tokens fields
        """
        # Generate query embedding
        query_embedding = self.embedding_engine.encode(prompt)

        scored = []
        for rec in candidates:
            # Get or generate embedding for candidate
            candidate_embedding = self._get_or_generate_embedding(rec)

            if candidate_embedding is None:
                continue  # Skip if embedding unavailable

            # Calculate semantic similarity
            similarity = self.embedding_engine.cosine_similarity(
                query_embedding, candidate_embedding
            )

            # Apply time decay
            if time_decay_hours > 0:
                age_hours = (
                    datetime.now(timezone.utc)
                    - self._parse_timestamp(rec["timestamp"])
                ).total_seconds() / 3600
                decay = math.exp(-age_hours / time_decay_hours)
                score = similarity * decay
            else:
                score = similarity

            rec["_score"] = score
            rec["_est_tokens"] = self._estimate_tokens(rec)
            scored.append(rec)

        return scored

    def _score_hybrid(
        self,
        prompt: str,
        candidates: List[Dict[str, Any]],
        time_decay_hours: int,
    ) -> List[Dict[str, Any]]:
        """
        Score candidates using hybrid approach (70% semantic + 30% keywords).

        Args:
            prompt: Query prompt
            candidates: Candidate conversation records
            time_decay_hours: Time decay factor

        Returns:
            List of scored records with _score and _est_tokens fields
        """
        # Get keyword scores
        query_tokens = self._extract_keywords(prompt)
        keyword_scores = {}
        for rec in candidates:
            score = self._score_record(
                rec, query_tokens, time_decay_hours=time_decay_hours
            )
            keyword_scores[rec["id"]] = score

        # Get semantic scores
        semantic_scored = self._score_semantic(prompt, candidates, time_decay_hours)

        # Combine: 70% semantic + 30% keywords
        scored = []
        for rec in semantic_scored:
            semantic_score = rec["_score"]
            keyword_score = keyword_scores.get(rec["id"], 0.0)
            hybrid_score = 0.7 * semantic_score + 0.3 * keyword_score

            rec["_score"] = hybrid_score
            scored.append(rec)

        return scored

    def _get_or_generate_embedding(self, record: Dict[str, Any]) -> Optional[Any]:
        """
        Get embedding from record or generate if missing.

        Args:
            record: Conversation record

        Returns:
            Embedding numpy array or None if unavailable
        """
        # Check if embedding exists
        if record.get("embedding"):
            try:
                return EmbeddingEngine.deserialize_embedding(record["embedding"])
            except Exception:
                pass  # Fall through to generation

        # Generate on-demand if missing
        try:
            text = f"{record['prompt']}\n{record['response'][:200]}"
            embedding = self.embedding_engine.encode(text)

            # Update database with new embedding (async, fire-and-forget)
            try:
                serialized = EmbeddingEngine.serialize_embedding(embedding)
                self.backend._conn.execute(
                    "UPDATE conversations SET embedding = ? WHERE id = ?",
                    (serialized, record["id"]),
                )
                self.backend._conn.commit()
            except Exception:
                pass  # Continue even if update fails

            return embedding
        except Exception:
            return None  # Embedding unavailable


# Global singleton instance
memory = MemoryEngine()
