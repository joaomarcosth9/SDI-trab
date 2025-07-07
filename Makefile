# cluster/Makefile
PYTHON := python3
N ?= 3               # qtd. de nós (override: make N=5 run)

run:
	$(PYTHON) -m src.node --id $${ID:-1}

run-n:
	@for i in $(shell seq 1 $(N)); do \
	    ID=$$i $(PYTHON) -m src.node --id $$i --nodes $(N) & \
		sleep 7; \
	done

