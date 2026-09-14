PY ?= python3
.PHONY: setup dataset test lint sim-server intake tick simulate accounting verify-chain dashboard demo deploy destroy

setup:
	$(PY) -m pip install -e ".[dev]"

dataset:
	$(PY) scripts/make_dataset.py

test:
	$(PY) -m pytest

lint:
	ruff check src tests scripts

sim-server:
	$(PY) -m postscript.sim.server

intake:
	postscript intake

tick:
	postscript tick

simulate:
	postscript simulate --weeks 8

accounting:
	postscript accounting --out out/accounting_alvarez.pdf

verify-chain:
	postscript verify-chain

dashboard:
	postscript dashboard

demo:
	postscript simulate --weeks 8 --speed 1.4 & \
	postscript dashboard

deploy:
	bash infra/deploy.sh

destroy:
	bash infra/destroy.sh
