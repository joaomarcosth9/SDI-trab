PYTHON := python3
N ?= 3               # qtd. de nós (override: make N=5 run)
OFF ?= 0          # deslocamento de ID (override: make OFF=2 run-n)

run:
	$(PYTHON) -m src.node --id $${ID:-1}

run-n:
	@for i in $(shell seq 1 $(N)); do \
	    ID=$$((i + $(OFF))) $(PYTHON) -m src.node --id $$((i + $(OFF))) & \
		sleep 0; \
	done
