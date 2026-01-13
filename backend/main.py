import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add CME_ODE to path
sys.path.insert(0, '/app/CME_ODE/program')

app = FastAPI(
    title="Minimal Cell Simulation API",
    description="API for running minimal cell model simulations with configurable parameters",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIMULATIONS_DIR = Path("/app/simulations")
SIMULATIONS_DIR.mkdir(exist_ok=True)

simulations_db: Dict[str, Dict[str, Any]] = {}


class SimulationRequest(BaseModel):
    simulation_time: float = Field(default=125.0, ge=1.0, le=500.0)
    restart_interval: float = Field(default=1.0, ge=0.1, le=10.0)
    simulation_type: str = Field(default="cme-ode", pattern="^(cme-ode|rdme)$")
    random_seed: Optional[int] = None
    custom_parameters: Optional[Dict[str, Any]] = None


class SimulationStatus(BaseModel):
    simulation_id: str
    status: str
    simulation_type: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: Optional[float] = None
    error_message: Optional[str] = None
    result_files: Optional[List[str]] = None


class SimulationResult(BaseModel):
    simulation_id: str
    status: str
    metadata: Dict[str, Any]
    data_summary: Optional[Dict[str, Any]] = None
    download_urls: Optional[List[str]] = None


def run_cme_ode_simulation(
    simulation_id: str,
    simulation_time: float,
    restart_interval: float,
    random_seed: Optional[int],
    custom_parameters: Optional[Dict[str, Any]]
):
    try:
        simulations_db[simulation_id]["status"] = "running"
        simulations_db[simulation_id]["started_at"] = datetime.utcnow().isoformat()

        sim_output_dir = SIMULATIONS_DIR / simulation_id
        sim_output_dir.mkdir(exist_ok=True)

        # TODO: Implement actual simulation execution
        for progress in [25, 50, 75, 100]:
            simulations_db[simulation_id]["progress_percent"] = progress

        metadata = {
            "simulation_time": simulation_time,
            "restart_interval": restart_interval,
            "random_seed": random_seed,
            "custom_parameters": custom_parameters or {},
            "completed_at": datetime.utcnow().isoformat()
        }

        with open(sim_output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        with open(sim_output_dir / "results.json", "w") as f:
            json.dump({
                "message": "Simulation completed",
                "simulation_id": simulation_id,
                "parameters": metadata
            }, f, indent=2)

        simulations_db[simulation_id]["status"] = "completed"
        simulations_db[simulation_id]["completed_at"] = datetime.utcnow().isoformat()
        simulations_db[simulation_id]["progress_percent"] = 100.0
        simulations_db[simulation_id]["result_files"] = ["metadata.json", "results.json"]

    except Exception as e:
        simulations_db[simulation_id]["status"] = "failed"
        simulations_db[simulation_id]["error_message"] = str(e)
        simulations_db[simulation_id]["completed_at"] = datetime.utcnow().isoformat()


@app.get("/")
async def root():
    return {
        "service": "Minimal Cell Simulation API",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_simulations": len([s for s in simulations_db.values() if s["status"] == "running"])
    }


@app.post("/simulations", response_model=SimulationStatus)
async def create_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    simulation_id = str(uuid.uuid4())

    simulations_db[simulation_id] = {
        "simulation_id": simulation_id,
        "status": "pending",
        "simulation_type": request.simulation_type,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress_percent": 0.0,
        "error_message": None,
        "result_files": None
    }

    if request.simulation_type == "cme-ode":
        background_tasks.add_task(
            run_cme_ode_simulation,
            simulation_id,
            request.simulation_time,
            request.restart_interval,
            request.random_seed,
            request.custom_parameters
        )
    else:
        simulations_db[simulation_id]["status"] = "failed"
        simulations_db[simulation_id]["error_message"] = "RDME not implemented"

    return SimulationStatus(**simulations_db[simulation_id])


@app.get("/simulations", response_model=List[SimulationStatus])
async def list_simulations(status: Optional[str] = None, limit: int = 50):
    simulations = list(simulations_db.values())
    if status:
        simulations = [s for s in simulations if s["status"] == status]
    simulations.sort(key=lambda x: x["created_at"], reverse=True)
    return [SimulationStatus(**s) for s in simulations[:limit]]


@app.get("/simulations/{simulation_id}", response_model=SimulationStatus)
async def get_simulation_status(simulation_id: str):
    if simulation_id not in simulations_db:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationStatus(**simulations_db[simulation_id])


@app.get("/simulations/{simulation_id}/results", response_model=SimulationResult)
async def get_simulation_results(simulation_id: str):
    if simulation_id not in simulations_db:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = simulations_db[simulation_id]
    if simulation["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Simulation not completed (status: {simulation['status']})")

    sim_output_dir = SIMULATIONS_DIR / simulation_id
    metadata_file = sim_output_dir / "metadata.json"

    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

    return SimulationResult(
        simulation_id=simulation_id,
        status=simulation["status"],
        metadata=metadata,
        data_summary={"message": "Results available for download"},
        download_urls=[f"/simulations/{simulation_id}/files/{f}" for f in simulation["result_files"] or []]
    )


@app.delete("/simulations/{simulation_id}")
async def delete_simulation(simulation_id: str):
    if simulation_id not in simulations_db:
        raise HTTPException(status_code=404, detail="Simulation not found")

    del simulations_db[simulation_id]

    sim_output_dir = SIMULATIONS_DIR / simulation_id
    if sim_output_dir.exists():
        import shutil
        shutil.rmtree(sim_output_dir)

    return {"message": "Simulation deleted", "simulation_id": simulation_id}


@app.get("/parameters/defaults")
async def get_default_parameters():
    return {
        "simulation_time": 125.0,
        "restart_interval": 1.0,
        "simulation_type": "cme-ode"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
