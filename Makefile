.PHONY: install run-api run-ui agent-ask agent-chain agent-last lint test clean memory-init memory-sync memory-note memory-log

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
		echo "Usage: make agent-chain Q='<question>'"; \
		exit 1; \
	fi
	. .venv/bin/activate && curl -X POST http://localhost:5050/chain \
		-H "Content-Type: application/json" \
		-d '{"prompt": "$(Q)"}'

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
