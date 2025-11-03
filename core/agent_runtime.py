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
        Route prompt to appropriate agent.

        Args:
            prompt: User prompt to route

        Returns:
            Agent name (builder, critic, or closer)
        """
        router_config = self.config["agents"].get("router")
        if not router_config:
            return "builder"  # Default fallback

        response = self.connector.call(
            model=router_config["model"],
            system=router_config["system"],
            user=prompt,
            temperature=router_config.get("temperature", 0.1),
            max_tokens=router_config.get("max_tokens", 10),
        )

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
        Run agent with prompt.

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

        # Call LLM
        llm_response: LLMResponse = self.connector.call(
            model=model,
            system=agent_config["system"],
            user=prompt,
            temperature=agent_config.get("temperature", 0.2),
            max_tokens=agent_config.get("max_tokens", 1500),
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
        )

        return result

    def chain(
        self, prompt: str, stages: Optional[List[str]] = None
    ) -> List[RunResult]:
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
                context = f"Original request: {prompt}\n\n{summary}\n\nYour task as {agent}:"

            result = self.run(agent=agent, prompt=context)
            results.append(result)

        return results
