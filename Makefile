PYTHON := python3
N ?= 3

.PHONY: all run run1 run2 run3 kill watch clean run-n kill-leader run-uuid

all: run

run-uuid:
	@echo "Starting $(N) nodes with UUID-based IDs..."
	@for i in $$(seq 1 $(N)); do \
		uuid=$$($(PYTHON) -c "import random; print(random.getrandbits(64) % 10000)"); \
		short_id=$$uuid; \
		echo "Starting node $$i: PID=$$uuid ($$short_id)"; \
		$(PYTHON) -m src.node --id $$uuid 2>&1 | sed "s/\[PID $$uuid\]/[$$short_id]/g" & \
	done
	@sleep 1
	@echo "All $(N) nodes started with UUID-based IDs"

run:
	@if [ -z "$$ID" ]; then \
		echo "Please set the ID environment variable (e.g., 'ID=1 make run')"; \
		exit 1; \
	fi
	@echo "Starting node with ID=$$ID..."
	@$(PYTHON) -m src.node --id $$ID

run-n:
	@echo "Starting $(N) nodes..."
	@for i in $$(seq 1 $(N)); do \
		echo "Starting node $$i"; \
		$(PYTHON) -m src.node --id $$i & \
	done
	@sleep 1
	@echo "All $(N) nodes started"

kill:
	@echo "Killing all node processes..."
	@pkill -f "python -m src.node" || true
	@pkill -f "python3 -m src.node" || true
	@echo "All processes killed."

kill-leader:
	@echo "Finding and killing leader (highest PID)..."
	@ps aux | grep -E "python.*src\.node.*--id" | grep -v grep | \
		awk '{for(i=1;i<=NF;i++) if($$i=="--id") print $$(i+1), $$2}' | \
		sort -n -k1 | tail -1 | awk '{print $$2}' | xargs -r kill -9 && \
		echo "Leader killed" || echo "No leader found"

watch:
	@watch -n 1 'ps aux | grep -E "python.*src\.node" | grep -v grep'

clean:
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache
	@echo "Cleanup complete."
