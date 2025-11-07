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

    def _compress_semantic(self, text: str, max_tokens: int = 500) -> str:
        """
        Extract semantic essence using structured JSON compression.

        Instead of truncating at arbitrary character limits, this method:
        - Extracts key decisions and rationale
        - Preserves technical specifications
        - Maintains trade-offs and open questions
        - Reduces tokens by ~90% while preserving 100% semantic information

        Args:
            text: Full output to compress
            max_tokens: Target token count (default: 500)

        Returns:
            Structured JSON summary as string
        """
        compression_prompt = f"""Summarize this output into structured JSON (max {max_tokens} tokens):

REQUIRED JSON STRUCTURE:
{{
  "key_decisions": ["decision1", "decision2", ...],
  "rationale": {{"decision1": "why chosen", "decision2": "why chosen"}},
  "trade_offs": ["trade-off 1", "trade-off 2", ...],
  "open_questions": ["question 1", "question 2", ...],
  "technical_specs": {{"component": "choice", "framework": "name"}}
}}

RULES:
- Extract ONLY the most important decisions and their reasoning
- Include ALL technical specifications mentioned
- Preserve trade-offs and concerns
- List unresolved questions or dependencies
- NO code snippets in summary (only decision: "use pattern X")
- Keep total output under {max_tokens} tokens

ORIGINAL OUTPUT TO SUMMARIZE:
{text}"""

        try:
            # Use fast, cheap model for compression
            response = self.connector.call(
                model="gemini/gemini-flash-latest",
                system="You are a semantic compression agent. Extract structured summaries from technical outputs.",
                user=compression_prompt,
                temperature=0.1,
                max_tokens=max_tokens,
            )

            if response.error or not response.text:
                # Fallback to intelligent truncation if compression fails
                return self._intelligent_truncate(text, max_tokens * 4)  # 4 chars ≈ 1 token

            return response.text
        except Exception:
            # Fallback to intelligent truncation on any error
            return self._intelligent_truncate(text, max_tokens * 4)

    def _intelligent_truncate(self, text: str, max_chars: int) -> str:
        """
        Fallback truncation that tries to end at sentence boundaries.

        Args:
            text: Text to truncate
            max_chars: Maximum characters

        Returns:
            Truncated text ending at sentence boundary if possible
        """
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        # Find last sentence end
        last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))

        if last_period > max_chars * 0.5:  # If sentence end is in second half
            return truncated[:last_period + 1]
        else:
            return truncated + "..."

    def _extract_critical_issues(self, critique_text: str) -> Optional[str]:
        """
        Extract critical issues from critic's response that require builder refinement.

        Looks for issues marked as:
        - CRITICAL, ERROR, SECURITY, BUG keywords (from config)
        - "Issue N:" patterns with severity indicators
        - Technical errors that must be fixed

        Args:
            critique_text: Full text from critic agent

        Returns:
            Formatted string of critical issues, or None if no critical issues found
        """
        import re

        if not critique_text:
            return None

        # Load keywords from config
        refinement_config = self.config.get("refinement", {})
        critical_keywords = refinement_config.get("critical_keywords", [
            "CRITICAL", "ERROR", "BUG", "SECURITY", "VULNERABILITY",
            "INCORRECT", "WRONG", "MISSING", "BROKEN", "FAILED"
        ])

        # Split into lines for analysis
        lines = critique_text.split('\n')
        critical_lines = []
        issue_blocks = []
        current_block = []
        in_critical_section = False

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Check if line contains critical keywords
            has_critical = any(keyword in line_upper for keyword in critical_keywords)

            # Check for issue patterns with severity
            issue_pattern = re.match(r'^\s*(?:Issue|Problem)\s+\d+:', line, re.IGNORECASE)

            if has_critical or issue_pattern:
                in_critical_section = True
                current_block = [line]
            elif in_critical_section:
                # Continue collecting lines for this issue block
                if line.strip() and not line.startswith('**'):
                    current_block.append(line)
                else:
                    # End of current block
                    if current_block:
                        issue_blocks.append('\n'.join(current_block))
                        current_block = []
                    in_critical_section = False

        # Add last block if exists
        if current_block:
            issue_blocks.append('\n'.join(current_block))

        # If no structured blocks found, fall back to line-by-line extraction
        if not issue_blocks:
            for line in lines:
                line_upper = line.upper()
                if any(keyword in line_upper for keyword in critical_keywords):
                    critical_lines.append(line.strip())

            if critical_lines:
                return '\n'.join(critical_lines)
            return None

        # Format the extracted issues
        if issue_blocks:
            formatted = "CRITICAL ISSUES REQUIRING FIXES:\n\n"
            for i, block in enumerate(issue_blocks, 1):
                formatted += f"{i}. {block}\n\n"
            return formatted.strip()

        return None

    def _check_convergence(self, current_issues: Optional[str], previous_issues: Optional[str]) -> tuple[bool, str]:
        """
        Check if refinement has converged (no more critical issues or no progress).

        Convergence criteria:
        1. No critical issues in current response (SUCCESS)
        2. Same or more issues than previous iteration (NO PROGRESS)
        3. Issue count decreased (PROGRESS - continue)

        Args:
            current_issues: Critical issues from current critic response
            previous_issues: Critical issues from previous critic response

        Returns:
            Tuple of (converged: bool, reason: str)
        """
        # Case 1: No critical issues found - CONVERGED (success)
        if current_issues is None:
            return (True, "No critical issues found - refinement successful")

        # Case 2: First iteration - always continue
        if previous_issues is None:
            return (False, "First iteration - continuing refinement")

        # Count issues in both responses (simple line count heuristic)
        current_issue_count = len([line for line in current_issues.split('\n') if line.strip()])
        previous_issue_count = len([line for line in previous_issues.split('\n') if line.strip()])

        # Case 3: More issues than before - CONVERGED (regression)
        if current_issue_count >= previous_issue_count:
            return (True, f"No progress detected ({previous_issue_count} → {current_issue_count} issues) - stopping")

        # Case 4: Fewer issues - PROGRESS (continue)
        return (False, f"Progress detected ({previous_issue_count} → {current_issue_count} issues) - continuing")

    def _merge_critic_consensus(self, critic_results: List[tuple[str, str]]) -> str:
        """
        Merge feedback from multiple critics into weighted consensus.

        Args:
            critic_results: List of (critic_name, response) tuples

        Returns:
            Merged consensus feedback with weighted prioritization
        """
        if not critic_results:
            return ""

        # Load consensus config
        multi_critic_config = self.config.get("multi_critic", {})
        consensus_config = multi_critic_config.get("consensus", {})
        threshold = consensus_config.get("threshold", 2)
        weights = consensus_config.get("weights", {})

        # Extract issues from each critic
        critic_issues = {}
        for critic_name, response in critic_results:
            issues = response.strip().split('\n')
            critic_issues[critic_name] = [issue.strip() for issue in issues if issue.strip()]

        # Build consensus
        consensus_parts = []
        consensus_parts.append("=== MULTI-CRITIC CONSENSUS ===\n")

        # Add each critic's feedback with weight indicator
        for critic_name, response in critic_results:
            weight = weights.get(critic_name, 1.0)
            weight_indicator = "⚠️ HIGH PRIORITY" if weight > 1.0 else "📋 STANDARD"

            consensus_parts.append(f"\n--- {critic_name.upper()} {weight_indicator} ---")
            consensus_parts.append(response)
            consensus_parts.append("")

        # Add summary
        total_critics = len(critic_results)
        consensus_parts.append(f"\n=== CONSENSUS SUMMARY ===")
        consensus_parts.append(f"Total critics analyzed: {total_critics}")

        # Count issues per critic
        for critic_name, issues in critic_issues.items():
            issue_count = len(issues)
            consensus_parts.append(f"- {critic_name}: {issue_count} issues found")

        return '\n'.join(consensus_parts)

    def _select_relevant_critics(self, prompt: str, builder_response: str) -> List[str]:
        """
        Dynamically select relevant critics based on prompt content (v0.10.0).

        Uses keyword-based classification to determine which critics are needed.
        Example: "Create HTML page" → only code-quality-critic
                 "Build JWT auth API" → all three critics

        Args:
            prompt: Original user prompt
            builder_response: Builder's output (for additional context)

        Returns:
            List of selected critic names (e.g., ["security-critic", "code-quality-critic"])
        """
        dynamic_config = self.config.get("dynamic_selection", {})

        # If dynamic selection disabled, return all critics
        if not dynamic_config.get("enabled", False):
            multi_critic_config = self.config.get("multi_critic", {})
            return multi_critic_config.get("critics", [])

        # Combine prompt and builder response for analysis
        combined_text = f"{prompt}\n{builder_response}".lower()

        # Score each critic based on keyword matches
        keywords_config = dynamic_config.get("keywords", {})
        critic_scores = {}

        for critic_name, keywords in keywords_config.items():
            score = 0
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Count occurrences (more mentions = higher relevance)
                score += combined_text.count(keyword_lower)
            critic_scores[critic_name] = score

        # Select critics with score > 0
        selected_critics = [critic for critic, score in critic_scores.items() if score > 0]

        # Apply min/max constraints
        min_critics = dynamic_config.get("min_critics", 1)
        max_critics = dynamic_config.get("max_critics", 3)

        # If no critics selected, use fallback
        if len(selected_critics) == 0:
            fallback = dynamic_config.get("fallback_critics", ["code-quality-critic"])
            selected_critics = fallback
            print(f"⚠️  No keywords matched - using fallback critics: {', '.join(fallback)}")

        # Enforce min_critics
        if len(selected_critics) < min_critics:
            # Add highest-scored unselected critics
            all_critics_sorted = sorted(critic_scores.items(), key=lambda x: x[1], reverse=True)
            for critic, _ in all_critics_sorted:
                if critic not in selected_critics:
                    selected_critics.append(critic)
                    if len(selected_critics) >= min_critics:
                        break

        # Enforce max_critics (prioritize by score)
        if len(selected_critics) > max_critics:
            # Sort by score descending, take top N
            selected_with_scores = [(c, critic_scores.get(c, 0)) for c in selected_critics]
            selected_with_scores.sort(key=lambda x: x[1], reverse=True)
            selected_critics = [c for c, _ in selected_with_scores[:max_critics]]

        # Log selection with scores
        print(f"🎯 Dynamic critic selection (keyword-based):")
        for critic in selected_critics:
            score = critic_scores.get(critic, 0)
            print(f"   ✓ {critic} (relevance score: {score})")

        skipped = [c for c in critic_scores.keys() if c not in selected_critics]
        if skipped:
            print(f"   ✗ Skipped: {', '.join(skipped)} (not relevant)")

        return selected_critics

    def _run_multi_critic(self, builder_response: str, original_prompt: str) -> tuple[str, List[RunResult]]:
        """
        Run multiple specialized critics in parallel and merge consensus.

        Args:
            builder_response: The builder's output to critique
            original_prompt: Original user prompt for context

        Returns:
            Tuple of (consensus_feedback, list of critic RunResults)
        """
        import concurrent.futures

        # Load multi-critic config
        multi_critic_config = self.config.get("multi_critic", {})
        if not multi_critic_config.get("enabled", False):
            # Fallback to single critic
            return ("", [])

        # DYNAMIC CRITIC SELECTION (v0.10.0)
        # Select relevant critics based on prompt content
        critic_names = self._select_relevant_critics(original_prompt, builder_response)
        parallel = multi_critic_config.get("parallel_execution", True)

        print(f"🔍 Running {len(critic_names)} specialized critics in parallel...\n")

        # Prepare critic context
        compression_threshold = 1200
        response_text = builder_response
        if len(response_text) > compression_threshold:
            compressed = self._compress_semantic(response_text, max_tokens=500)
            response_text = f"{compressed}\n\n[Note: Above is structured summary preserving all key decisions and specs]"

        critic_context = f"Original request: {original_prompt}\n\nBuilder output:\n{response_text}\n\nYour task as critic:"

        # Run critics
        critic_results = []
        run_results = []

        if parallel:
            # Parallel execution using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(critic_names)) as executor:
                future_to_critic = {
                    executor.submit(self.run, critic_name, critic_context): critic_name
                    for critic_name in critic_names
                }

                for future in concurrent.futures.as_completed(future_to_critic):
                    critic_name = future_to_critic[future]
                    try:
                        result = future.result()
                        critic_results.append((critic_name, result.response))
                        run_results.append(result)
                        print(f"✅ {critic_name} complete ({result.total_tokens} tokens)")
                    except Exception as e:
                        print(f"❌ {critic_name} failed: {e}")
        else:
            # Sequential execution
            for critic_name in critic_names:
                print(f"🔍 Running {critic_name}...")
                result = self.run(critic_name, critic_context)
                critic_results.append((critic_name, result.response))
                run_results.append(result)
                print(f"✅ {critic_name} complete ({result.total_tokens} tokens)")

        # Merge consensus
        consensus = self._merge_critic_consensus(critic_results)

        return (consensus, run_results)

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
        self, agent: str, prompt: str, override_model: Optional[str] = None, mock_mode: Optional[bool] = None
    ) -> RunResult:
        """
        Run agent with prompt and fallback support.

        Args:
            agent: Agent name (auto, builder, critic, closer)
            prompt: User prompt
            override_model: Optional model override
            mock_mode: Optional mock mode override (defaults to LLM_MOCK env var)

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

                    # Estimate injected tokens using standardized counting
                    from config.settings import count_tokens
                    injected_context_tokens = count_tokens(context_block)
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
            mock_mode=mock_mode,
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

    def chain(self, prompt: str, stages: Optional[List[str]] = None, progress_callback=None, enable_refinement: Optional[bool] = None, mock_mode: Optional[bool] = None) -> List[RunResult]:
        """
        Execute multi-agent chain with optional single-iteration refinement.

        Args:
            prompt: Initial user prompt
            stages: List of agent names (default: builder -> critic -> closer)
            progress_callback: Optional function(stage_num, total, agent_name) to report progress
            enable_refinement: If True, allows builder to refine based on critical issues (default: from config)
            mock_mode: Optional mock mode override (defaults to LLM_MOCK env var)

        Returns:
            List of RunResults from each stage
        """
        if stages is None:
            stages = ["builder", "critic", "closer"]

        # Load refinement setting from config if not explicitly provided
        if enable_refinement is None:
            refinement_config = self.config.get("refinement", {})
            enable_refinement = refinement_config.get("enabled", True)

        results = []
        context = prompt
        refinement_triggered = False

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
                        # Use semantic compression for long outputs
                        compression_threshold = 1500
                        response_text = prev.response

                        if len(response_text) > compression_threshold:
                            # Semantic compression preserves meaning while reducing tokens
                            compressed = self._compress_semantic(response_text, max_tokens=500)
                            response_text = f"{compressed}\n\n[Note: Above is structured summary. Full output: {len(response_text)} chars]"

                        context += f"=== {prev.agent.upper()} OUTPUT ===\n{response_text}\n\n"

                    context += f"Your task as {agent}: Synthesize all above outputs into a coherent final plan."

                else:
                    # Standard sequential: critic sees builder, etc.
                    prev_result = results[-1]

                    # Semantic compression threshold
                    # Memory-enabled agents: 800 chars (they have historical context)
                    # Non-memory agents: 1200 chars (need more immediate context)
                    compression_threshold = 1200 if not has_memory else 800

                    response_text = prev_result.response

                    if len(response_text) > compression_threshold:
                        # Use semantic compression to preserve all key information
                        compressed = self._compress_semantic(response_text, max_tokens=500)
                        response_text = f"{compressed}\n\n[Note: Above is structured summary preserving all key decisions and specs]"

                    summary = f"Previous {prev_result.agent} output:\n{response_text}"
                    context = (
                        f"Original request: {prompt}\n\n{summary}\n\nYour task as {agent}:"
                    )

            # MULTI-CRITIC EXECUTION: Replace single critic with parallel multi-critic consensus
            if agent == "critic":
                # Check if multi-critic is enabled
                multi_critic_config = self.config.get("multi_critic", {})
                if multi_critic_config.get("enabled", False):
                    # Find builder result for multi-critic analysis
                    builder_result = results[-1] if results else None
                    if builder_result and builder_result.agent == "builder":
                        # Run multi-critic consensus
                        consensus, critic_run_results = self._run_multi_critic(builder_result.response, prompt)

                        # Create synthetic result for consensus (for compatibility with existing flow)
                        # Use the first critic's metadata but with consensus response
                        if critic_run_results:
                            first_critic = critic_run_results[0]
                            result = RunResult(
                                agent="multi-critic",
                                model=f"consensus-{len(critic_run_results)}-critics",
                                provider="multi",
                                prompt=context,
                                response=consensus,
                                duration_ms=sum(r.duration_ms for r in critic_run_results),
                                prompt_tokens=sum(r.prompt_tokens for r in critic_run_results),
                                completion_tokens=sum(r.completion_tokens for r in critic_run_results),
                                total_tokens=sum(r.total_tokens for r in critic_run_results),
                                timestamp=first_critic.timestamp,
                                log_file="multi-critic-consensus",
                            )
                            # Store all critic results
                            results.extend(critic_run_results)
                        else:
                            # Fallback to single critic if multi-critic failed
                            result = self.run(agent=agent, prompt=context, mock_mode=mock_mode)
                    else:
                        # No builder result, use single critic
                        result = self.run(agent=agent, prompt=context, mock_mode=mock_mode)
                else:
                    # Multi-critic disabled, use single critic
                    result = self.run(agent=agent, prompt=context, mock_mode=mock_mode)
            else:
                # Non-critic agents use standard execution
                result = self.run(agent=agent, prompt=context, mock_mode=mock_mode)

            results.append(result)

            # MULTI-ITERATION REFINEMENT: After critic/multi-critic stage, iteratively refine until convergence
            if enable_refinement and result.agent in ["critic", "multi-critic"] and not refinement_triggered:
                critical_issues = self._extract_critical_issues(result.response)

                if critical_issues:
                    refinement_triggered = True

                    # Load max_iterations from config
                    refinement_config = self.config.get("refinement", {})
                    max_iterations = refinement_config.get("max_iterations", 3)

                    # Track iterations
                    iteration = 1
                    previous_issues = None
                    converged = False
                    convergence_reason = ""

                    print(f"\n🔄 Critical issues detected! Starting multi-iteration refinement (max {max_iterations} iterations)...\n")

                    while iteration <= max_iterations and not converged:
                        # Check convergence
                        if iteration > 1:  # Skip convergence check on first iteration
                            converged, convergence_reason = self._check_convergence(critical_issues, previous_issues)

                            if converged:
                                print(f"✅ Convergence achieved after {iteration-1} iteration(s): {convergence_reason}\n")
                                break

                        # Store current issues for next iteration
                        previous_issues = critical_issues

                        # Find the most recent builder result
                        builder_index = -2 if iteration == 1 else -1  # First iteration: before critic, later: last result
                        if len(results) >= 2:
                            # Create refinement prompt for builder
                            refine_prompt = f"""Original request: {prompt}

Your previous solution had the following CRITICAL ISSUES identified by the critic (iteration {iteration}):

{critical_issues}

Please provide an IMPROVED version of your solution that addresses these critical issues.
Focus on:
1. Fixing technical errors
2. Addressing security concerns
3. Resolving missing components
4. Correcting incorrect implementations

Provide a complete, refined solution."""

                            # Report progress if callback provided
                            builder_label = f"builder-v{iteration+1}"
                            if progress_callback:
                                progress_callback(len(results) + 1, len(stages) + iteration, builder_label)

                            print(f"🔄 Iteration {iteration}/{max_iterations}: Running {builder_label}...")

                            # Run builder again with refinement prompt
                            refined_result = self.run(agent="builder", prompt=refine_prompt)
                            results.append(refined_result)

                            print(f"✅ {builder_label} complete ({refined_result.total_tokens} tokens)\n")

                            # Re-run critic on the refined builder output
                            critic_label = f"critic-v{iteration+1}"

                            # Get compression threshold for critic
                            critic_cfg = self.config["agents"].get("critic", {})
                            has_critic_memory = critic_cfg.get("memory_enabled", False)
                            compression_threshold = 1200 if not has_critic_memory else 800

                            response_text = refined_result.response
                            if len(response_text) > compression_threshold:
                                compressed = self._compress_semantic(response_text, max_tokens=500)
                                response_text = f"{compressed}\n\n[Note: Above is structured summary preserving all key decisions and specs]"

                            critic_context = f"Original request: {prompt}\n\nPrevious builder output (iteration {iteration+1}):\n{response_text}\n\nYour task as critic:"

                            if progress_callback:
                                progress_callback(len(results) + 1, len(stages) + iteration, critic_label)

                            print(f"🔄 Iteration {iteration}/{max_iterations}: Running {critic_label}...")

                            # Run critic on refined output
                            critic_result = self.run(agent="critic", prompt=critic_context)
                            results.append(critic_result)

                            # Extract issues from new critic response
                            critical_issues = self._extract_critical_issues(critic_result.response)

                            if critical_issues:
                                print(f"⚠️  {critic_label} found critical issues ({critic_result.total_tokens} tokens)\n")
                            else:
                                print(f"✅ {critic_label} found no critical issues - refinement successful! ({critic_result.total_tokens} tokens)\n")
                                converged = True
                                convergence_reason = "No critical issues found"
                                break

                            iteration += 1

                    # Final convergence message
                    if iteration > max_iterations and not converged:
                        print(f"⏹️  Max iterations ({max_iterations}) reached - stopping refinement\n")

        return results
