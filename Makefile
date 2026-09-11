PYTHON ?= python

.PHONY: agents check test evidence test-all

agents:
	$(PYTHON) scripts/sync_agent_guides.py --write

check:
	$(PYTHON) scripts/check_architecture_contracts.py

test:
	$(PYTHON) -m unittest discover -s tests -v

evidence:
	$(PYTHON) scripts/reproduce_contact_validation.py

test-all: check test evidence
