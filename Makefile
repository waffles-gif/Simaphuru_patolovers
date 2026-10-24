.PHONY: install test lint demo experiment
PYTHON ?= python

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

demo:
	$(PYTHON) -m streamlit run app.py

experiment:
	$(PYTHON) -m quantum.run_qaoa --input data/model_output.json --out artifacts/team_two.json
