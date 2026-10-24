"""Contrato compartido. Cualquier cambio de semántica exige actualizar MODEL_VERSION."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODEL_VERSION = "queue-network-v1"


class Blockage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    junction: int = Field(ge=0, description="Índice de cruce: C1 es 0")
    start_s: int = Field(ge=0)
    duration_s: int = Field(gt=0)
    capacity_factor: float = Field(ge=0, le=1)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    junctions: int = Field(ge=2, le=5)
    horizon_s: int = Field(default=680, ge=1, le=3600)
    storage_vehicles: int = Field(default=12, ge=1)
    travel_time_s: int = Field(default=20, ge=1)
    service_veh_s: float = Field(default=0.5, gt=0, le=1)
    main_veh_min: float = Field(default=14, ge=0, le=120)
    side_veh_min: float = Field(default=6, ge=0, le=120)
    arrival_mode: Literal["uniform", "poisson"] = "uniform"
    peak_start_s: int = Field(default=240, ge=0)
    peak_end_s: int = Field(default=420, ge=0)
    peak_factor: float = Field(default=1, ge=0, le=5)
    blockages: tuple[Blockage, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self):
        if self.peak_end_s < self.peak_start_s:
            raise ValueError("peak_end_s debe ser >= peak_start_s")
        if any(b.junction >= self.junctions for b in self.blockages):
            raise ValueError("Bloqueo asociado a un cruce inexistente")
        return self

    def fingerprint(self, seed: int) -> str:
        payload = {"scenario": self.model_dump(), "seed": seed, "model": MODEL_VERSION}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.model_validate_json(Path(path).read_text(encoding="utf-8"))


def decision_vector(index: int, size: int) -> tuple[int, ...]:
    """El bit de peso 2**i representa Ci+1 y el qubit i de Qiskit."""
    return tuple((index >> i) & 1 for i in range(size))


def decision_label(index: int, size: int) -> str:
    """Etiqueta humana C1…Cn, inversa al ket habitual de Qiskit."""
    return "".join(map(str, decision_vector(index, size)))
