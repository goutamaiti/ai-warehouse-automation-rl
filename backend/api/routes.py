"""HTTP routes of the warehouse dashboard API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services import simulation_service as service

router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    """Body of ``POST /api/run``."""

    scenario: str = Field(default="default", description="scenario file name")
    controller: str = Field(default="astar", description="astar | bfs | random | ppo")
    seed: int = Field(default=0, ge=0, le=2**31 - 1, description="episode seed")


def _handle(call, *args, **kwargs):
    """Run a service call, translating service errors into HTTP 404/400."""
    try:
        return call(*args, **kwargs)
    except service.ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe, also used by the frontend to detect a running backend."""
    return {"status": "ok", "controllers": service.available_controllers()}


@router.get("/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return service.list_scenarios()


@router.get("/scenarios/{name}/layout")
def layout(name: str) -> dict[str, Any]:
    return _handle(service.get_layout, name)


@router.get("/episodes")
def episodes() -> list[dict[str, Any]]:
    return service.list_recorded_episodes()


@router.get("/episodes/{episode_id}")
def episode(episode_id: str) -> dict[str, Any]:
    return _handle(service.load_recorded_episode, episode_id)


@router.get("/results")
def results() -> list[dict[str, Any]]:
    return service.list_results()


@router.post("/run")
def run(request: RunRequest) -> dict[str, Any]:
    """Run one episode live and return the full replay."""
    return _handle(
        service.run_live_episode, request.scenario, request.controller, request.seed
    )


@router.get("/run")
def run_via_get(
    scenario: str = Query(default="default"),
    controller: str = Query(default="astar"),
    seed: int = Query(default=0, ge=0, le=2**31 - 1),
) -> dict[str, Any]:
    """Convenience GET variant, handy for quick checks from the browser."""
    return _handle(service.run_live_episode, scenario, controller, seed)
