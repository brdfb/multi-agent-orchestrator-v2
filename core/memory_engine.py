"""Memory engine for persistent conversation storage and retrieval."""

from typing import Any, Dict, List, Optional

from core.memory_backend import SQLiteBackend


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
            self._initialized = True

    def store_conversation(
        self,
        prompt: str,
        response: str,
        agent: str,
        model: str,
        provider: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Store conversation to memory.

        Args:
            prompt: User prompt
            response: Agent response
            agent: Agent name (builder, critic, closer, etc.)
            model: Model identifier
            provider: Provider name (openai, anthropic, google)
            metadata: Additional metadata (tokens, cost, duration, etc.)

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
        self, prompt: str, max_tokens: int = 500, agent: Optional[str] = None
    ) -> str:
        """
        Get relevant context from past conversations for a prompt.

        Uses simple keyword matching to find relevant conversations.
        Future: Upgrade to semantic search with embeddings.

        Args:
            prompt: Current user prompt
            max_tokens: Maximum tokens for context
            agent: Filter by agent (optional)

        Returns:
            Formatted context string
        """
        if not self.enabled:
            return ""

        # Extract keywords from prompt (simple approach)
        keywords = self._extract_keywords(prompt)

        if not keywords:
            # No keywords - return recent conversations
            conversations = self.get_recent_conversations(limit=3, agent=agent)
        else:
            # Search by keywords
            conversations = []
            for keyword in keywords[:3]:  # Try top 3 keywords
                results = self.search_conversations(query=keyword, agent=agent, limit=2)
                conversations.extend(results)

            # Remove duplicates
            seen = set()
            unique_conversations = []
            for conv in conversations:
                if conv["id"] not in seen:
                    seen.add(conv["id"])
                    unique_conversations.append(conv)
            conversations = unique_conversations[:5]  # Max 5 conversations

        if not conversations:
            return ""

        # Format context with token budgeting
        context_parts = []
        current_tokens = 0

        for conv in conversations:
            # Estimate tokens (rough: 4 chars = 1 token)
            conv_text = f"[Past conversation]\nQ: {conv['prompt']}\nA: {conv['response'][:200]}..."
            estimated_tokens = len(conv_text) // 4

            if current_tokens + estimated_tokens > max_tokens:
                break

            context_parts.append(conv_text)
            current_tokens += estimated_tokens

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    def _extract_keywords(self, text: str, min_length: int = 4) -> List[str]:
        """
        Extract keywords from text (simple word extraction).

        Args:
            text: Input text
            min_length: Minimum word length

        Returns:
            List of keywords
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
        keywords = [
            w.strip(".,!?;:")
            for w in words
            if len(w) >= min_length and w.lower() not in stop_words
        ]

        return keywords[:10]  # Return top 10 keywords

    def enable(self):
        """Enable memory system."""
        self.enabled = True

    def disable(self):
        """Disable memory system."""
        self.enabled = False


# Global singleton instance
memory = MemoryEngine()
