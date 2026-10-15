# Thin wrapper; the real work is in tasks.py (so Windows works without make).
PY ?= python

.PHONY: seed dev test demo
seed:
	$(PY) tasks.py seed
dev:
	$(PY) tasks.py dev
test:
	$(PY) tasks.py test
demo:
	$(PY) tasks.py demo
