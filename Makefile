.PHONY: install run-api run-ui agent-ask agent-chain agent-last lint test clean memory-init memory-sync memory-note memory-log memory-search memory-recent memory-stats memory-cleanup memory-export

install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run-api:
	. .venv/bin/activate && uvicorn api.server:app --reload --host 0.0.0.0 --port 5050

run-ui:
	@echo "UI is served by the API server. Access at http://localhost:5050"
	$(MAKE) run-api

agent-ask:
	@if [ -z "$(AGENT)" ] || [ -z "$(Q)" ]; then \
		echo "Usage: make agent-ask AGENT=<agent> Q='<question>'"; \
		echo "  AGENT: auto, builder, critic, closer"; \
		exit 1; \
	fi
	. .venv/bin/activate && python scripts/agent_runner.py $(AGENT) "$(Q)"

agent-chain:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make agent-chain Q='<question>' [STAGES='agent1 agent2...']"; \
		echo "  Example: make agent-chain Q='Design API'"; \
		echo "  Example: make agent-chain Q='Review code' STAGES='builder critic'"; \
		exit 1; \
	fi
	. .venv/bin/activate && python scripts/chain_runner.py "$(Q)" $(STAGES)

agent-last:
	@ls -t data/CONVERSATIONS/*.json 2>/dev/null | head -1 | xargs cat | python3 -m json.tool || echo "No logs found"

lint:
	. .venv/bin/activate && ruff check . && black --check .

test:
	. .venv/bin/activate && pytest -q tests/

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Memory system targets
memory-init:
	./scripts/memory_post_setup.sh

memory-sync:
	~/memory/BIN/pm_sync_quickstart.sh

memory-note:
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make memory-note MSG='your note here'"; \
		exit 1; \
	fi
	@echo "[$(shell date -Iseconds)] $(MSG)" >> ~/memory/NOTES/$(shell basename $(CURDIR)).notes
	@echo "Note added to ~/memory/NOTES/$(shell basename $(CURDIR)).notes"

memory-log:
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make memory-log MSG='your log entry'"; \
		exit 1; \
	fi
	@~/memory/BIN/pm_log.sh "$(shell basename $(CURDIR))" "$(MSG)"

# Memory CLI commands (conversation memory system)
memory-search:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make memory-search Q='query' [AGENT=agent] [LIMIT=10]"; \
		exit 1; \
	fi
	. .venv/bin/activate && python scripts/memory_cli.py search "$(Q)" \
		$(if $(AGENT),--agent $(AGENT)) \
		$(if $(LIMIT),--limit $(LIMIT))

memory-recent:
	. .venv/bin/activate && python scripts/memory_cli.py recent \
		$(if $(LIMIT),--limit $(LIMIT),--limit 10) \
		$(if $(AGENT),--agent $(AGENT))

memory-stats:
	. .venv/bin/activate && python scripts/memory_cli.py stats

memory-cleanup:
	. .venv/bin/activate && python scripts/memory_cli.py cleanup \
		$(if $(DAYS),--days $(DAYS),--days 90) \
		$(if $(CONFIRM),-y)

memory-export:
	. .venv/bin/activate && python scripts/memory_cli.py export \
		$(if $(FROM),--from-date $(FROM)) \
		$(if $(TO),--to-date $(TO)) \
		$(if $(FORMAT),--format $(FORMAT),--format json) \
		$(if $(LIMIT),--limit $(LIMIT))
