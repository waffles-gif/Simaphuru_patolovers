import copy
import itertools
import json
from pathlib import Path

import pytest

from model.traffic import simulate_chain
from simaphuru.team import default_team_params
from web.animation import animation_html, animation_payload


@pytest.mark.parametrize("fixture", ["team_two.json", "team_five.json"])
def test_recording_new_replay_fields_preserves_preexisting_reference_costs(fixture):
    root = Path(__file__).resolve().parents[1]
    reference = json.loads((root / "artifacts" / fixture).read_text())
    params = reference["inputs"]["params"]
    for old in reference["model"]["combinations"]:
        current = simulate_chain(list(old["plans"].values()), params, keep_history=True)
        assert current["total_cost"] == pytest.approx(old["total_cost"], abs=1e-8, rel=0)
        for name in ("peak_queue", "residual", "blocked_s"):
            assert current["metrics"][name] == old["metrics"][name]


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_recorded_blocking_events_match_counters_and_do_not_change_the_physics(n):
    params = default_team_params(n)
    for plans in itertools.product((0, 1), repeat=n):
        full = simulate_chain(list(plans), params, keep_history=True)
        without_history = simulate_chain(list(plans), params)
        assert full["metrics"] == without_history["metrics"]
        assert full["total_cost"] == without_history["total_cost"]
        for i, intersection in enumerate(full["per_intersection"]):
            assert sum(step["blocked"][i] for step in full["history"]) == intersection["blocked_s"]
        for step in full["history"]:
            assert len(step["blocked"]) == n
            assert not step["blocked"][-1]
            for i, blocked in enumerate(step["blocked"]):
                if blocked:
                    assert step["phases"][i] == "EW"
                    assert step["departures"][i]["EW"] == 0


def test_payload_uses_original_snapshot_times_and_all_fields_without_modifying_history():
    params = default_team_params(2)
    result = simulate_chain([0, 1], params, keep_history=True)
    selected = {"plans": {"A": 0, "B": 1}, "history": result["history"]}
    original = copy.deepcopy(selected)
    payload = animation_payload(selected, params)
    for expected, actual in zip(selected["history"], payload["history"]):
        assert actual == expected
    assert payload["plans"] == [0, 1]
    assert selected == original
    # Un historial anterior sigue siendo legible; no se inventa su evento de bloqueo.
    for step in selected["history"]:
        del step["blocked"]
    assert all(step["blocked"] is None for step in animation_payload(selected, params)["history"])


def test_renderer_rejects_mixed_network_shapes_and_escapes_script_identifiers():
    params = default_team_params(2)
    result = simulate_chain([0, 0], params, keep_history=True)
    selected = {"plans": {"A": 0, "B": 0}, "history": result["history"]}
    bad = copy.deepcopy(selected)
    bad["history"][0]["queues"].pop()
    with pytest.raises(ValueError, match="número de cruces"):
        animation_payload(bad, params)
    malicious = "</script><script>alert(1)</script>"
    params["intersections"][0]["id"] = malicious
    selected["plans"] = {malicious: 0, "B": 0}
    html = animation_html(selected, params)
    assert malicious not in html
    assert "\\u003c/script>" in html
