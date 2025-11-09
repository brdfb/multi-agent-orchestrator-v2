"""
Context Aggregator for Multi-Agent Orchestrator

Implements dual-context model:
1. Session Context: Recent messages from same session (devamlılık)
2. Knowledge Context: Semantic search from other sessions (alakalı bilgi)

Features:
- Priority-based token budget (session gets up to 75%, knowledge uses remaining)
- Flexible allocation (maximizes context usage)
- Smart truncation (preserves important content)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import count_tokens
from core.memory_engine import MemoryEngine


class ContextAggregator:
    """
    Aggregates session and knowledge context for LLM calls.

    Dual-context model ensures both conversation continuity
    and cross-session knowledge retrieval.
    """

    def __init__(self):
        self.memory = MemoryEngine()

    def get_full_context(
        self,
        prompt: str,
        session_id: Optional[str],
        config: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Aggregate session context + knowledge context.

        Args:
            prompt: User's current prompt
            session_id: Current session ID (None = no session context)
            config: Agent memory config from agents.yaml

        Returns:
            Tuple of (formatted_context_string, metadata_dict)

        Example metadata:
            {
                'session_context_tokens': 250,
                'knowledge_context_tokens': 300,
                'total_context_tokens': 550,
                'session_messages': 3,
                'knowledge_messages': 2
            }
        """
        contexts = []
        metadata = {
            'session_context_tokens': 0,
            'knowledge_context_tokens': 0,
            'total_context_tokens': 0,
            'session_messages': 0,
            'knowledge_messages': 0
        }

        # 1. SESSION CONTEXT (recent conversation in this session)
        session_config = config.get('session_context', {})
        if session_id and session_config.get('enabled', True):
            session_conv = self._get_session_conversations(
                session_id=session_id,
                limit=session_config.get('limit', 5)
            )

            if session_conv:
                session_text = self._format_session_context(session_conv)
                session_tokens = count_tokens(session_text)

                contexts.append({
                    'type': 'session',
                    'text': session_text,
                    'tokens': session_tokens,
                    'priority': 1,  # Highest priority
                    'count': len(session_conv)
                })

        # 2. KNOWLEDGE CONTEXT (semantic search, exclude current session)
        knowledge_config = config.get('knowledge_context', {})
        if knowledge_config.get('enabled', True):
            knowledge_conv = self._get_knowledge_conversations(
                prompt=prompt,
                exclude_session_id=session_id,
                config=knowledge_config
            )

            if knowledge_conv:
                knowledge_text = self._format_knowledge_context(knowledge_conv)
                knowledge_tokens = count_tokens(knowledge_text)

                contexts.append({
                    'type': 'knowledge',
                    'text': knowledge_text,
                    'tokens': knowledge_tokens,
                    'priority': 2,  # Lower priority
                    'count': len(knowledge_conv)
                })

        # 3. TOKEN BUDGET ENFORCEMENT (Flexible allocation with priority)
        max_tokens = config.get('max_context_tokens', 600)
        selected = self._apply_token_budget_with_priority(contexts, max_tokens)

        # 4. FORMAT FINAL CONTEXT
        final_context = self._format_final_context(selected)

        # 5. UPDATE METADATA
        for ctx in selected:
            if ctx['type'] == 'session':
                metadata['session_context_tokens'] = ctx['tokens']
                metadata['session_messages'] = ctx['count']
            elif ctx['type'] == 'knowledge':
                metadata['knowledge_context_tokens'] = ctx['tokens']
                metadata['knowledge_messages'] = ctx['count']

        metadata['total_context_tokens'] = sum(ctx['tokens'] for ctx in selected)

        return final_context, metadata

    def _get_session_conversations(
        self,
        session_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations from same session.

        Args:
            session_id: Session ID
            limit: Max number of conversations

        Returns:
            List of conversation dicts (most recent first)
        """
        import sqlite3
        from pathlib import Path

        db_path = Path("data/MEMORY/conversations.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, timestamp, agent, prompt, response
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))

            rows = cursor.fetchall()

            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'agent': row[2],
                    'prompt': row[3],
                    'response': row[4]
                }
                for row in rows
            ]

        finally:
            conn.close()

    def _get_knowledge_conversations(
        self,
        prompt: str,
        exclude_session_id: Optional[str],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get relevant conversations via semantic search (excluding current session).

        Args:
            prompt: Current prompt
            exclude_session_id: Session ID to exclude
            config: Knowledge context config

        Returns:
            List of conversation dicts with scores
        """
        # Use memory engine's existing search API
        # For now, get recent conversations and manually filter by session
        # This is a simplified approach - full semantic search would require
        # accessing the embedding search functionality

        try:
            # Get recent conversations (last 50)
            recent = self.memory.get_recent_conversations(limit=50)

            # Filter out current session
            filtered = []
            for conv in recent:
                if exclude_session_id and conv.get('session_id') == exclude_session_id:
                    continue
                # Simple relevance based on keyword match
                prompt_lower = prompt.lower()
                conv_prompt_lower = conv.get('prompt', '').lower()

                # Basic keyword overlap
                prompt_words = set(prompt_lower.split())
                conv_words = set(conv_prompt_lower.split())
                overlap = len(prompt_words & conv_words) / max(len(prompt_words), 1)

                if overlap > 0.1:  # At least 10% overlap
                    conv['_score'] = overlap
                    filtered.append(conv)

            # Sort by score
            filtered.sort(key=lambda x: x.get('_score', 0), reverse=True)

            return filtered[:10]

        except Exception:
            # Graceful degradation - return empty list
            return []

    def _format_session_context(self, conversations: List[Dict[str, Any]]) -> str:
        """
        Format session conversations (recent messages in same session).

        Example output:
        ```
        [SESSION CONTEXT - Recent conversation]

        [3 messages ago]
        User: "Python'da matplotlib ile chart nasıl çizilir?"
        Assistant: "İşte basit bir bar chart örneği: ..."

        [1 message ago]
        User: "Chart'a kırmızı renk ekle"
        Assistant: "Renk eklemek için colors parametresini kullan: ..."
        ```

        Args:
            conversations: List of conversation dicts (most recent first)

        Returns:
            Formatted string
        """
        if not conversations:
            return ""

        parts = ["[SESSION CONTEXT - Recent conversation]\n"]

        # Reverse to chronological order (oldest first)
        for i, conv in enumerate(reversed(conversations)):
            age = len(conversations) - i
            age_str = f"{age} message{'s' if age > 1 else ''} ago"

            parts.append(f"[{age_str}]")
            parts.append(f"User: \"{conv['prompt'][:150]}{'...' if len(conv['prompt']) > 150 else ''}\"")

            # Truncate response to first 300 chars
            response_snippet = conv['response'][:300]
            if len(conv['response']) > 300:
                response_snippet += "..."

            parts.append(f"Assistant: \"{response_snippet}\"\n")

        return "\n".join(parts)

    def _format_knowledge_context(self, conversations: List[Dict[str, Any]]) -> str:
        """
        Format knowledge conversations (semantic search from other sessions).

        Example output:
        ```
        [KNOWLEDGE CONTEXT - Relevant past topics]

        [Relevance: 0.82, 2 days ago]
        Topic: JWT authentication implementation
        Summary: "JWT tokens için PyJWT library kullan..."

        [Relevance: 0.65, 1 week ago]
        Topic: FastAPI middleware best practices
        Summary: "Custom middleware için @app.middleware decorator kullan..."
        ```

        Args:
            conversations: List of conversation dicts with _score

        Returns:
            Formatted string
        """
        if not conversations:
            return ""

        parts = ["[KNOWLEDGE CONTEXT - Relevant past topics]\n"]

        for conv in conversations:
            score = conv.get('_score', 0.0)
            age = self._calculate_message_age(conv['timestamp'])

            parts.append(f"[Relevance: {score:.2f}, {age}]")
            parts.append(f"Topic: {conv['prompt'][:80]}")

            # Truncate response to first 200 chars
            response_snippet = conv['response'][:200]
            if len(conv['response']) > 200:
                response_snippet += "..."

            parts.append(f"Summary: \"{response_snippet}\"\n")

        return "\n".join(parts)

    def _calculate_message_age(self, timestamp: str) -> str:
        """
        Calculate human-readable age of message.

        Args:
            timestamp: ISO timestamp string

        Returns:
            Human-readable age (e.g., "2 minutes ago", "3 hours ago", "2 days ago")
        """
        try:
            msg_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(msg_time.tzinfo) if msg_time.tzinfo else datetime.now()
            delta = now - msg_time

            seconds = delta.total_seconds()

            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                days = int(seconds / 86400)
                return f"{days} day{'s' if days > 1 else ''} ago"

        except Exception:
            return "unknown age"

    def _apply_token_budget_with_priority(
        self,
        contexts: List[Dict[str, Any]],
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Apply token budget with priority-based flexible allocation.

        Strategy:
        1. Session context gets priority (up to 75% of budget)
        2. Knowledge context uses remaining tokens
        3. If session < 75%, knowledge can use the rest

        This prevents session overflow while maximizing context usage.

        Args:
            contexts: List of context dicts with 'type', 'text', 'tokens', 'priority'
            max_tokens: Total budget

        Returns:
            Selected contexts within budget (may be truncated)

        Example:
            max_tokens = 600
            session_max = 450 (75%)

            Case 1: Session needs 300 tokens
            → Session gets 300, Knowledge gets 300 (uses remaining 300)

            Case 2: Session needs 500 tokens
            → Session gets 450 (75% cap), Knowledge gets 150

            Case 3: Session needs 100 tokens
            → Session gets 100, Knowledge gets 500 (uses remaining 500)
        """
        if not contexts:
            return []

        selected = []
        session_max = int(max_tokens * 0.75)  # 75% cap for session
        remaining_budget = max_tokens

        # Sort by priority (1 = highest)
        sorted_contexts = sorted(contexts, key=lambda x: x['priority'])

        for ctx in sorted_contexts:
            if ctx['type'] == 'session':
                # Session gets priority, but capped at 75%
                allocated = min(ctx['tokens'], session_max, remaining_budget)
            else:
                # Knowledge uses remaining budget
                allocated = min(ctx['tokens'], remaining_budget)

            if allocated > 0:
                # Truncate context if needed
                if allocated < ctx['tokens']:
                    ctx['text'] = self._truncate_to_tokens(ctx['text'], allocated)
                    ctx['tokens'] = allocated

                selected.append(ctx)
                remaining_budget -= allocated

            if remaining_budget <= 0:
                break

        return selected

    def _truncate_to_tokens(self, text: str, target_tokens: int) -> str:
        """
        Truncate text to fit target token count.

        Simple approximation: ~4 chars per token for English/Turkish.

        Args:
            text: Text to truncate
            target_tokens: Target token count

        Returns:
            Truncated text
        """
        estimated_chars = target_tokens * 4
        if len(text) <= estimated_chars:
            return text

        return text[:estimated_chars] + "...\n[Context truncated to fit budget]"

    def _format_final_context(self, contexts: List[Dict[str, Any]]) -> str:
        """
        Format selected contexts into final string.

        Args:
            contexts: Selected context dicts

        Returns:
            Formatted context string
        """
        if not contexts:
            return ""

        parts = []

        for ctx in sorted(contexts, key=lambda x: x['priority']):
            if ctx['text'].strip():
                parts.append(ctx['text'])

        return "\n\n".join(parts)


def get_context_aggregator() -> ContextAggregator:
    """Get or create ContextAggregator singleton."""
    global _context_aggregator

    if '_context_aggregator' not in globals():
        globals()['_context_aggregator'] = ContextAggregator()

    return globals()['_context_aggregator']
