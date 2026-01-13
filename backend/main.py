"""
Minimal Cell Simulation API

REST API for running and monitoring cell simulations.
"""

import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
import worker


# Initialize FastAPI app
app = FastAPI(
    title="Minimal Cell Simulation API",
    description="API for running and monitoring JCVI-Syn3A minimal cell simulations",
    version="0.1.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Pydantic Models -----

class SimulationConfig(BaseModel):
    """Configuration for a new simulation."""
    total_time_seconds: int = Field(
        default=3600,
        ge=1,
        le=36000,
        description="Total simulation time in seconds (1-36000)"
    )
    timestep: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Time between result saves in seconds"
    )


class SimulationCreate(BaseModel):
    """Request body for creating a simulation."""
    config: Optional[SimulationConfig] = None


class SimulationResponse(BaseModel):
    """Response model for simulation data."""
    id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    total_time_seconds: int
    current_time_seconds: int
    progress_percent: float


class ResultResponse(BaseModel):
    """Response model for a single result."""
    time_seconds: float
    metabolites: Optional[dict] = None
    fluxes: Optional[dict] = None
    cell_metrics: Optional[dict] = None


class ResultsResponse(BaseModel):
    """Response model for multiple results."""
    simulation_id: str
    count: int
    results: List[dict]


# ----- Startup -----

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    database.init_db()


# ----- Health Endpoints -----

@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Minimal Cell Simulation API", "status": "running"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ----- Simulation Endpoints -----

@app.post("/simulations", response_model=SimulationResponse)
def create_simulation(body: SimulationCreate = None):
    """
    Create and start a new simulation.

    Returns the simulation ID which can be used to query status and results.
    """
    # Generate unique ID
    simulation_id = str(uuid.uuid4())

    # Get config or defaults
    config = body.config if body and body.config else SimulationConfig()

    # Create database record
    database.create_simulation(
        simulation_id=simulation_id,
        config=config.model_dump(),
        total_time_seconds=config.total_time_seconds
    )

    # Start simulation worker
    worker.start_simulation(
        simulation_id=simulation_id,
        total_time_seconds=config.total_time_seconds,
        timestep=config.timestep
    )

    # Return simulation info
    return _get_simulation_response(simulation_id)


@app.get("/simulations", response_model=List[SimulationResponse])
def list_simulations(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """
    List all simulations.

    Returns simulations ordered by creation time (most recent first).
    """
    simulations = database.list_simulations(limit=limit, offset=offset)
    return [_make_simulation_response(s) for s in simulations]


@app.get("/simulations/{simulation_id}", response_model=SimulationResponse)
def get_simulation(simulation_id: str):
    """
    Get simulation status and metadata.
    """
    return _get_simulation_response(simulation_id)


@app.delete("/simulations/{simulation_id}")
def delete_simulation(simulation_id: str):
    """
    Cancel a running simulation or delete a completed one.
    """
    sim = database.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Stop if running
    if sim['status'] == 'running':
        worker.stop_simulation(simulation_id)

    # Delete from database
    database.delete_simulation(simulation_id)

    return {"message": "Simulation deleted", "id": simulation_id}


@app.get("/simulations/{simulation_id}/results", response_model=ResultsResponse)
def get_results(
    simulation_id: str,
    after: Optional[float] = Query(
        default=None,
        description="Return results after this time (seconds)"
    ),
    limit: int = Query(default=1000, ge=1, le=10000)
):
    """
    Get simulation results.

    Use the `after` parameter for incremental polling:
    - First call: GET /simulations/{id}/results
    - Subsequent calls: GET /simulations/{id}/results?after={last_time}

    This allows efficient real-time updates without re-fetching all data.
    """
    sim = database.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    results = database.get_results(
        simulation_id=simulation_id,
        after_time=after,
        limit=limit
    )

    return {
        "simulation_id": simulation_id,
        "count": len(results),
        "results": results
    }


@app.get("/simulations/{simulation_id}/results/latest", response_model=ResultResponse)
def get_latest_result(simulation_id: str):
    """
    Get the most recent result for a simulation.

    Useful for displaying current state without fetching all history.
    """
    sim = database.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    result = database.get_latest_result(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="No results yet")

    return result


# ----- Helper Functions -----

def _get_simulation_response(simulation_id: str) -> SimulationResponse:
    """Get simulation and convert to response model."""
    sim = database.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _make_simulation_response(sim)


def _make_simulation_response(sim: dict) -> SimulationResponse:
    """Convert database row to response model."""
    total_time = sim.get('total_time_seconds', 3600)
    current_time = sim.get('current_time_seconds', 0)

    progress = (current_time / total_time * 100) if total_time > 0 else 0

    return SimulationResponse(
        id=sim['id'],
        status=sim['status'],
        created_at=sim['created_at'],
        started_at=sim.get('started_at'),
        completed_at=sim.get('completed_at'),
        error_message=sim.get('error_message'),
        total_time_seconds=total_time,
        current_time_seconds=current_time,
        progress_percent=round(progress, 2)
    )


# ----- Main -----

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
