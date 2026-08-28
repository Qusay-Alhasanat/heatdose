# api/models.py
"""
Pydantic response models. Every field here is a direct mirror of a shape
already defined and tested in data/ — this file adds validation and
OpenAPI docs, it does not invent any new shape. If a shape here ever
needs to change, check docs/data_contract.md first: that's the source
of truth, this file follows it.
"""

from __future__ import annotations

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lng: float


class ShiftPoint(BaseModel):
    """One point in a worker's shift trail — for the map's route line."""

    location: Location
    timestamp: str
    temp_c: float


class WorkerStatus(BaseModel):
    """Mirrors data/worker_status.get_worker_status() exactly."""

    worker_id: str
    profile: str
    shift_start_hour: int
    hours_elapsed: int
    current_location: Location
    current_zone: str
    current_temp_c: float
    total_dose: float
    excess_dose: float
    risk_level: str


class WorkerDetail(WorkerStatus):
    """WorkerStatus plus the full shift trail, for GET /api/workers/{id}."""

    shift: list[ShiftPoint]


class HeatmapPoint(BaseModel):
    """One grid tile — mirrors fortyguard_client.get_temperature_grid()."""

    location: Location
    temp_c: float


class CoolPointCandidate(BaseModel):
    """Mirrors cool_points.get_candidates_with_current_temp() — no
    temp_diff_c/distance_m here, those are only computed per-worker by
    find_nearest_cool_point(), which the agent calls, not this endpoint."""

    point_id: str
    zone_type: str
    location: Location
    temp_c: float


class CoolPointResult(BaseModel):
    """
    Mirrors find_nearest_cool_point()'s output, wrapped with a
    "reachable" flag. reachable=False is a valid, expected outcome
    (see data/cool_points.py) — not an error — so callers must check
    this field rather than assuming every worker has a route.
    """

    reachable: bool
    point_id: str | None = None
    zone_type: str | None = None
    location: Location | None = None
    temp_c: float | None = None
    temp_diff_c: float | None = None
    distance_m: int | None = None
    reason: str | None = None


class DoseRisk(BaseModel):
    excess_dose: float
    risk_level: str


class WorkerComparison(BaseModel):
    """Mirrors data/baseline.compare_worker() exactly."""

    worker_id: str
    hyperlocal: DoseRisk
    city_level: DoseRisk
    risk_underestimated: bool
    dose_difference: float


class ComparisonSummary(BaseModel):
    """Mirrors data/baseline.comparison_summary() exactly."""

    total_workers: int
    underestimated_count: int
    underestimated_workers: list[str]
    comparisons: dict[str, WorkerComparison]


class AgentQueryRequest(BaseModel):
    question: str


class ToolTraceEntry(BaseModel):
    tool: str
    args: dict
    result: dict | list | str | float | int | bool | None


class AgentQueryResponse(BaseModel):
    answer: str
    tool_trace: list[ToolTraceEntry]


class HealthResponse(BaseModel):
    status: str
