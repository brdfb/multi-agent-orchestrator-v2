"""Agent runtime orchestration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import load_agents_config
from core.llm_connector import LLMConnector, LLMResponse
from core.logging_utils import write_json


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
        }


class AgentRuntime:
    """Orchestrates agent execution."""

    def __init__(self):
        self.config = load_agents_config()
        self.connector = LLMConnector(retry_count=1)

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

        # Call LLM with fallback support
        llm_response: LLMResponse = self.connector.call(
            model=model,
            system=agent_config["system"],
            user=prompt,
            temperature=agent_config.get("temperature", 0.2),
            max_tokens=agent_config.get("max_tokens", 1500),
            fallback_order=fallback_order,
        )

        # Create log record
        timestamp = datetime.utcnow().isoformat()
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
        )

        return result

    def chain(self, prompt: str, stages: Optional[List[str]] = None) -> List[RunResult]:
        """
        Execute multi-agent chain.

        Args:
            prompt: Initial user prompt
            stages: List of agent names (default: builder -> critic -> closer)

        Returns:
            List of RunResults from each stage
        """
        if stages is None:
            stages = ["builder", "critic", "closer"]

        results = []
        context = prompt

        for i, agent in enumerate(stages):
            # For stages after the first, add context from previous
            if i > 0:
                prev_result = results[-1]
                # Create summary to avoid token explosion
                summary = f"Previous {prev_result.agent} output (summarized): {prev_result.response[:200]}..."
                context = (
                    f"Original request: {prompt}\n\n{summary}\n\nYour task as {agent}:"
                )

            result = self.run(agent=agent, prompt=context)
            results.append(result)

        return results
