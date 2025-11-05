"""Agent runtime orchestration."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.settings import load_agents_config, load_memory_config
from core.llm_connector import LLMConnector, LLMResponse
from core.logging_utils import write_json
from core.memory_engine import MemoryEngine


@dataclass
class RunResult:
    """Result from agent execution."""

    agent: str
    model: str
    provider: str
    prompt: str
    response: str
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: str
    log_file: str
    error: Optional[str] = None
    original_model: Optional[str] = None  # If fallback was used
    fallback_reason: Optional[str] = None  # Why fallback was triggered
    fallback_used: bool = False  # Whether fallback was triggered
    injected_context_tokens: int = 0  # Tokens from memory context injection

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent": self.agent,
            "model": self.model,
            "provider": self.provider,
            "prompt": self.prompt,
            "response": self.response,
            "duration_ms": self.duration_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp,
            "log_file": self.log_file,
            "error": self.error,
            "original_model": self.original_model,
            "fallback_reason": self.fallback_reason,
            "fallback_used": self.fallback_used,
        }


class AgentRuntime:
    """Orchestrates agent execution."""

    def __init__(self):
        self.config = load_agents_config()
        self.memory_config = load_memory_config()
        self.connector = LLMConnector(retry_count=1)
        self._memory = None  # Lazy initialization
        # Generate session ID for this runtime instance
        self.session_id = datetime.now(timezone.utc).isoformat()

    @property
    def memory(self) -> MemoryEngine:
        """Lazy initialization of memory engine."""
        if self._memory is None:
            self._memory = MemoryEngine()
        return self._memory

    def route(self, prompt: str) -> str:
        """
        Route prompt to appropriate agent with fallback support.

        Args:
            prompt: User prompt to route

        Returns:
            Agent name (builder, critic, or closer)
        """
        router_config = self.config["agents"].get("router")
        if not router_config:
            return "builder"  # Default fallback

        # Get fallback order for router
        fallback_order = router_config.get("fallback_order", [])

        response = self.connector.call(
            model=router_config["model"],
            system=router_config["system"],
            user=prompt,
            temperature=router_config.get("temperature", 0.1),
            max_tokens=router_config.get("max_tokens", 10),
            fallback_order=fallback_order,
        )

        # If router call failed completely, default to builder
        if response.error:
            return "builder"

        # Extract agent name from response
        agent = response.text.strip().lower()

        # Validate agent name
        valid_agents = ["builder", "critic", "closer"]
        if agent not in valid_agents:
            return "builder"  # Default fallback

        return agent

    def run(
        self, agent: str, prompt: str, override_model: Optional[str] = None
    ) -> RunResult:
        """
        Run agent with prompt and fallback support.

        Args:
            agent: Agent name (auto, builder, critic, closer)
            prompt: User prompt
            override_model: Optional model override

        Returns:
            RunResult with response and metadata
        """
        # Handle auto-routing
        if agent == "auto":
            agent = self.route(prompt)

        # Get agent config
        agent_config = self.config["agents"].get(agent)
        if not agent_config:
            raise ValueError(f"Unknown agent: {agent}")

        # Determine model to use
        model = override_model if override_model else agent_config["model"]

        # Get fallback order (only if not using override)
        fallback_order = None
        if not override_model:
            fallback_order = agent_config.get("fallback_order", [])

        # Memory context injection
        system_prompt = agent_config["system"]
        injected_context_tokens = 0

        if agent_config.get("memory_enabled", False):
            try:
                # Get agent-specific memory config (with global defaults)
                agent_memory_config = agent_config.get("memory", {})
                global_memory_config = self.memory_config.get("memory", {})

                # Merge configs (agent-specific overrides global)
                max_tokens = agent_memory_config.get(
                    "max_context_tokens",
                    global_memory_config.get("context", {}).get(
                        "max_context_tokens_default", 350
                    ),
                )
                min_relevance = agent_memory_config.get(
                    "min_relevance",
                    global_memory_config.get("filtering", {}).get(
                        "min_relevance", 0.35
                    ),
                )
                time_decay_hours = agent_memory_config.get(
                    "time_decay_hours",
                    global_memory_config.get("filtering", {}).get(
                        "time_decay_hours", 96
                    ),
                )
                exclude_same_turn = agent_memory_config.get(
                    "exclude_same_turn",
                    global_memory_config.get("filtering", {}).get(
                        "exclude_same_turn", True
                    ),
                )

                # Get context from memory
                memory_context = self.memory.get_context_for_prompt(
                    prompt,
                    strategy=agent_memory_config.get("strategy", "keywords"),
                    max_tokens=max_tokens,
                    min_relevance=min_relevance,
                    time_decay_hours=time_decay_hours,
                    exclude_current_session=exclude_same_turn,
                    agent=agent,  # Filter by current agent
                    session_id=self.session_id,
                )

                # Inject context if available
                if memory_context:
                    # Add context header from config
                    context_header = global_memory_config.get("context", {}).get(
                        "prompt_header",
                        "[MEMORY CONTEXT - Relevant past conversations]\n",
                    )
                    context_block = f"{context_header}{memory_context}"

                    # Inject into system prompt
                    system_prompt = f"{agent_config['system']}\n\n{context_block}"

                    # Estimate injected tokens (4 chars ≈ 1 token)
                    injected_context_tokens = len(context_block) // 4
            except Exception:
                # If memory retrieval fails (e.g., database not available), continue without context
                # This ensures graceful degradation in test/development environments
                pass

        # Call LLM with fallback support
        llm_response: LLMResponse = self.connector.call(
            model=model,
            system=system_prompt,
            user=prompt,
            temperature=agent_config.get("temperature", 0.2),
            max_tokens=agent_config.get("max_tokens", 1500),
            fallback_order=fallback_order,
        )

        # Create log record
        timestamp = datetime.now(timezone.utc).isoformat()
        log_record = {
            "agent": agent,
            "model": llm_response.model,
            "provider": llm_response.provider,
            "prompt": prompt,
            "response": llm_response.text,
            "duration_ms": llm_response.duration_ms,
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
            "total_tokens": llm_response.total_tokens,
            "timestamp": timestamp,
            "error": llm_response.error,
            "injected_context_tokens": injected_context_tokens,
        }

        # Add fallback metadata if applicable
        if llm_response.original_model:
            log_record["original_model"] = llm_response.original_model
            log_record["fallback_reason"] = llm_response.fallback_reason
            log_record["fallback_used"] = True
        else:
            log_record["fallback_used"] = False

        # Write log
        log_file = write_json(log_record)

        # Auto-store conversation to memory (if agent has memory enabled)
        if agent_config.get("memory_enabled", False) and not llm_response.error:
            try:
                self.memory.store_conversation(
                    prompt=prompt,
                    response=llm_response.text,
                    agent=agent,
                    model=llm_response.model,
                    provider=llm_response.provider,
                    metadata={
                        "duration_ms": llm_response.duration_ms,
                        "prompt_tokens": llm_response.prompt_tokens,
                        "completion_tokens": llm_response.completion_tokens,
                        "total_tokens": llm_response.total_tokens,
                        "estimated_cost_usd": llm_response.estimated_cost,
                        "fallback_used": llm_response.original_model is not None,
                        "original_model": llm_response.original_model,
                        "fallback_reason": llm_response.fallback_reason,
                        "session_id": self.session_id,
                        "injected_context_tokens": injected_context_tokens,
                    },
                )
            except Exception as e:
                # If memory storage fails, continue (graceful degradation)
                # Log the error for debugging
                import sys
                print(f"⚠️  Memory storage failed: {e}", file=sys.stderr)

        # Create result
        result = RunResult(
            agent=agent,
            model=llm_response.model,
            provider=llm_response.provider,
            prompt=prompt,
            response=llm_response.text,
            duration_ms=llm_response.duration_ms,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            timestamp=timestamp,
            log_file=str(log_file.name),
            error=llm_response.error,
            original_model=llm_response.original_model,
            fallback_reason=llm_response.fallback_reason,
            fallback_used=llm_response.original_model is not None,
            injected_context_tokens=injected_context_tokens,
        )

        return result

    def chain(self, prompt: str, stages: Optional[List[str]] = None, progress_callback=None) -> List[RunResult]:
        """
        Execute multi-agent chain.

        Args:
            prompt: Initial user prompt
            stages: List of agent names (default: builder -> critic -> closer)
            progress_callback: Optional function(stage_num, total, agent_name) to report progress

        Returns:
            List of RunResults from each stage
        """
        if stages is None:
            stages = ["builder", "critic", "closer"]

        results = []
        context = prompt

        for i, agent in enumerate(stages):
            # Report progress if callback provided
            if progress_callback:
                progress_callback(i + 1, len(stages), agent)
            # For stages after the first, add context from previous
            if i > 0:
                agent_cfg = self.config["agents"].get(agent, {})
                has_memory = agent_cfg.get("memory_enabled", False)

                # Special handling for closer: needs ALL previous stages
                if agent == "closer":
                    # Closer sees full conversation history for synthesis
                    context = f"Original request: {prompt}\n\n"

                    for prev in results:
                        # More generous truncation for closer (needs full context)
                        max_chars = 1500
                        response_text = prev.response

                        if len(response_text) > max_chars:
                            truncated = response_text[:max_chars]
                            # Find last sentence end
                            last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
                            if last_period > max_chars * 0.5:
                                response_text = truncated[:last_period + 1]
                            else:
                                response_text = truncated + "..."

                        context += f"=== {prev.agent.upper()} OUTPUT ===\n{response_text}\n\n"

                    context += f"Your task as {agent}: Synthesize all above outputs into a coherent final plan."

                else:
                    # Standard sequential: critic sees builder, etc.
                    prev_result = results[-1]

                    # Memory-enabled agents can handle more context (they have history)
                    # Non-memory agents need fuller immediate context
                    max_chars = 1000 if not has_memory else 600

                    # Intelligent truncation: try to end at sentence boundary
                    response_text = prev_result.response
                    if len(response_text) > max_chars:
                        truncated = response_text[:max_chars]
                        # Find last sentence end
                        last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
                        if last_period > max_chars * 0.5:  # If sentence end is in second half
                            response_text = truncated[:last_period + 1]
                        else:
                            response_text = truncated + "..."

                    summary = f"Previous {prev_result.agent} output:\n{response_text}"
                    context = (
                        f"Original request: {prompt}\n\n{summary}\n\nYour task as {agent}:"
                    )

            result = self.run(agent=agent, prompt=context)
            results.append(result)

        return results
