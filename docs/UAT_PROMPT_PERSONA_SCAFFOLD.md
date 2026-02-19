# UAT Prompt: Persona Factory Scaffold (Orchestrator Chain Test)

**Context:** We have a multi-agent Orchestrator (builder → critic → closer). We want to introduce a "Persona Factory": a structured way to add domain personas (e.g. finance assistant, approval workflows) as standardized packs with three levels:

- **L1:** Tone, scope, conversation boundaries (soft)
- **L2:** Tools, memory policy, input/output contracts (semi-hard)
- **L3:** Permissions, approval gates, audit, fail-safes (hard)

Each persona is one versioned pack (single ID) with exactly 6 files; a "Persona Steward" role produces/validates these packs.

**Your task:**

1. **Design** a minimal "Scaffold v0" for this repo: folder layout under `personas/` (_framework/ with templates and rules, packs/ with one example pack), and the exact 6 file names and their roles.
2. **Integrate** with existing Orchestrator: how could a persona pack map to an agent (e.g. in config) so that chain or single-agent calls can use it? Propose one concrete option (e.g. "persona_id in agents.yaml" or "persona loader that generates agent config").
3. **Risks and guardrails:** What could go wrong if we add 5+ personas without this scaffold (spaghetti), and what single lint rule would you add first (P0) to prevent the worst failure?
4. **Deliverable:** A short implementation checklist (5–7 steps) to go from current repo state to "first persona pack loadable by the Orchestrator" without breaking existing builder/critic/closer flows.

Be concrete and specific. Output should be directly usable by a developer to implement Scaffold v0 and one baseline persona (e.g. FIN_BASELINE_ASSISTANT_v1).
