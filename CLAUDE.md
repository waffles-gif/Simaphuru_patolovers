# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Hackathon MVP (Qiskit Fall Fest 2026): connected-traffic corridor simulation + QUBO/QAOA signal-plan optimization. Code comments, docs, UI and commit messages are in Spanish; keep that convention.

## Commands

Setup (Python 3.13 recommended, 3.11–3.13 supported; CI runs 3.11 and 3.13):

```sh
py -3.13 -m venv .venv && .venv\Scripts\Activate.ps1   # Windows
python -m pip install -r requirements.txt               # editable install + dev extras, constrained by requirements.lock
```

- Tests: `python -m pytest` (testpaths: `tests/` and `model/test_traffic.py`)
- Single test: `python -m pytest tests/test_team_integration.py::test_name`
- Lint: `python -m ruff check .` (line length 100, rules E4/E7/E9/F/I)
- UI: `python -m streamlit run app.py`
- Headless pipeline:
  - `python model/enumerate.py --out data/model_output.json`
  - `python -m quantum.run_qaoa --input data/model_output.json --out artifacts/team_two.json`
  - `python -m quantum.run_qaoa --n 5 --out artifacts/team_five.json`
- `Makefile` wraps these (`install`, `test`, `lint`, `demo`, `experiment`).

Never edit `requirements.lock` by hand; it is regenerated from a clean environment. The main QAOA path uses `qiskit.quantum_info.Statevector` locally (not Aer) — no IBM account/token.

### Final extension, package/schema 0.3

`run_team_experiment` and the CLI accept `encoding="one_hot" | "binary"`; default remains one-hot.
Binary encoding is an exact algebraic substitution of the same local/neighbor factors, not a new
traffic model. Physical version and config_hash stay unchanged. Use `decision_index` for the active
probability register, `encoding` for qubit counts, `audit.encoding` for its proof and `experiment_id`
for execution identity. `audit.one_hot` is null for binary results. Consult `docs/CONTRACTS.md`.
The experimental schema 1.0 is unrelated even though it also uses one bit per crossing.

`python -m quantum.benchmark_encodings` runs paired encoding tests on three synthetic scenarios,
two network sizes and seeds 3/7/11. It records actual and maximum training budgets and physical
equality; timings are local simulation timings, not evidence of quantum advantage.

`--hybrid` adds verified candidate search (`simaphuru/hybrid.py`): DP initial solution, proposals
from ideal QAOA probabilities, uniform and local-search controls. Each method independently calls
the full simulator within equal upper budgets. The candidate selector must never receive the
exhaustive cost table or the physical optimum. This is not a warm-start quantum state.
Use `python -m quantum.benchmark_hybrid` for the ablation; include training costs and actual work.

The team UI now offers N=2,3,4,5 (all already supported by the backend). `web/animation.py` owns a
single playback clock shared by the canvas and its HTML cards; do not reintroduce a second Streamlit
time slider. `history[].blocked` records the actual service-check event, not a condition inferred
from post-service occupancy. It is additive history logging, with unchanged physical equations/costs.
Consult `docs/PLAYBACK_AND_CORRIDORS.md` and `tests/test_animation.py`.

## Architecture

Two independent engines coexist; `app.py` picks one via sidebar radio. Never mix their numbers, schemas or cost definitions.

**Default flow — team engine (schema 0.3, `TEAM_MODEL_VERSION = "team-ns-ew-v2"`, finite EW storage K_e + spillback):**

`model/traffic.py` (team's physics, R3) → `model/enumerate.py` / `model/chain.py` (all plan combinations, local + pairwise cost factors) → `quantum/qubo.py` (one-hot/binary QUBO, DP classical reference) → `simaphuru/quantum.py` (shared Qiskit QAOA circuits/training) → `simaphuru/team.py` (Pydantic validation, experiment schema 0.3, physical/execution fingerprints, optional verified hybrid search) → consumed by `web/team_app.py` and `quantum/run_qaoa.py` (CLI). Streamlit and CLI share the same path; there is no HTTP API or DB.

- `model/traffic.py` holds the team's original equations — preserve them; `model/enumerate.py` and `model/test_traffic.py` have ruff ignores to keep the team's style.
- Two crossings: QUBO reproduces costs exactly. Five crossings: the neighbor-pair QUBO is an approximation (audited over 1024 states) — never label it exact.
- Importing a 0.1 payload regenerates costs from the engine and rejects it if they differ by >1e-5; `example_result.json` (`example=true`, fake numbers) must be rejected as real input.

**Experimental flow — finite-storage engine (schema 1.0):** `simaphuru/models.py` (`Scenario`, `Blockage`), `simaphuru/simulation.py`, `simaphuru/experiment.py`, `simaphuru/cli.py` (`simaphuru` console script), UI in `web/reference_app.py`, scenarios in `data/scenarios/`. Uses one bit per crossing and a different cost. `docs/MODEL.md` describes only this engine. `simaphuru/qubo.py` is its QUBO/Ising container — don't confuse with `quantum/qubo.py`.

## Contracts (see `docs/CONTRACTS.md`)

- Bit order: variable q ↔ qubit q ↔ weight `2**q`; Qiskit kets print reversed. One-hot for two crossings is `x_A0,x_A1,x_B0,x_B1` (A=1,B=0 → index 6). Experimental engine: index `Σ xi·2**i`; use `decision_vector`/`decision_label` rather than parsing strings.
- Units are in field names (seconds, veh/min arrivals, veh/s service, 1 s step). Don't change units, cost, or bit order without updating contracts, the model version and tests.
- Schema 0.3 keeps the 0.1/0.2 model fields (`inputs`, `model.local_costs`, `model.pair_costs`, `model.combinations`, `classical`); `quantum` is null when QAOA isn't requested. `config_hash` covers all physical params + model version; `experiment_id` also identifies execution settings.
- Metric names are not interchangeable: `network_pending` includes queues, external backlog and in-transit vehicles; `metrics.residual` is queues + external EW backlog; `blocked_s` is report-only, not in the cost.
- Probabilities span all 16/1024 one-hot states including invalid ones; `conditional_expected_original` is over feasible states only.
- Parameters are synthetic/illustrative — don't claim empirical calibration (e.g. Javier Prado) or quantum advantage. New real data needs source, date, unit and scope.

## Repo conventions

- `artifacts/` is git-ignored except the four reference JSONs used to reproduce validation (`docs/VALIDATION.md`).
- Team works by role branches (`rol1/…` to `rol4/…`, see `docs/ROLES.md`) with PRs to `main`; keep changes inside the owning module.
- During the hackathon, pushing directly to `main` is allowed.
