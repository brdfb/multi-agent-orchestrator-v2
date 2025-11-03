# Shared Orchestrator Makefile
# Include in your project: include $(HOME)/.orchestrator/orchestrator.mk

ORCHESTRATOR_HOME ?= $(HOME)/.orchestrator

.PHONY: mao-ask mao-chain mao-last mao-help

mao-ask:
	@if [ -z "$(AGENT)" ] || [ -z "$(Q)" ]; then \
		echo "Usage: make mao-ask AGENT=<agent> Q='<question>'"; \
		echo "  AGENT: auto, builder, critic, closer"; \
		exit 1; \
	fi
	@cd $(ORCHESTRATOR_HOME) && . .venv/bin/activate && \
		python scripts/agent_runner.py $(AGENT) "$(Q)"

mao-chain:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make mao-chain Q='<question>'"; \
		exit 1; \
	fi
	@cd $(ORCHESTRATOR_HOME) && . .venv/bin/activate && \
		curl -X POST http://localhost:5050/chain \
		-H "Content-Type: application/json" \
		-d '{"prompt": "$(Q)"}' 2>/dev/null || \
		echo "⚠️  Orchestrator API not running. Start with: cd ~/.orchestrator && make run-api"

mao-last:
	@ls -t $(ORCHESTRATOR_HOME)/data/CONVERSATIONS/*.json 2>/dev/null | head -1 | \
		xargs cat 2>/dev/null | python3 -m json.tool || \
		echo "No conversations found"

mao-help:
	@echo "Multi-Agent Orchestrator - Shared Targets"
	@echo ""
	@echo "Available commands:"
	@echo "  make mao-ask AGENT=<agent> Q='<question>'"
	@echo "  make mao-chain Q='<question>'"
	@echo "  make mao-last"
	@echo ""
	@echo "Or use shell alias directly:"
	@echo "  mao auto 'Your question'"
	@echo "  mao builder 'Create a function...'"
