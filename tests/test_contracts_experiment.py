import json

import pytest
from pydantic import ValidationError

from simaphuru.experiment import run_experiment
from simaphuru.models import Scenario


def test_contract_rejects_unknown_fields_and_invalid_event():
    base = {"scenario_id": "test", "provenance": "sintético", "junctions": 2}
    with pytest.raises(ValidationError):
        Scenario(**base, arrival_rate=42)
    with pytest.raises(ValidationError):
        Scenario(
            **base, blockages=[{"junction": 2, "start_s": 0, "duration_s": 2, "capacity_factor": 0}]
        )


def test_experiment_is_json_serializable_and_configuration_is_identified():
    s = Scenario(
        scenario_id="integration",
        provenance="sintético",
        junctions=2,
        horizon_s=68,
        arrival_mode="poisson",
    )
    result = run_experiment(s, seed=3, qaoa=True, max_evaluations=8)
    json.dumps(result)
    assert result["audit"]["exact_representation"]
    assert len(result["evaluations"]) == 4
    assert result["config_hash"] == s.fingerprint(3)
    assert s.fingerprint(3) != s.fingerprint(4)
    assert s.fingerprint(3) != s.model_copy(update={"main_veh_min": 5}).fingerprint(3)
    assert not result["claims"]["empirically_calibrated"]
