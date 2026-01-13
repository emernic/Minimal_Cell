"""
Simulation worker module.

Handles running simulations in background threads/processes and
saving results to the database incrementally.
"""

import threading
import multiprocessing
import traceback
import logging
from typing import Dict, Optional
from datetime import datetime

import database
import simulation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimulationWorker:
    """
    Manages simulation execution in background.

    Uses threading for simplicity. Each simulation runs in its own thread
    and saves results to SQLite every timestep.
    """

    def __init__(self):
        self._running_simulations: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start_simulation(
        self,
        simulation_id: str,
        total_time_seconds: int = 3600,
        timestep: float = 1.0
    ) -> bool:
        """
        Start a simulation in a background thread.

        Args:
            simulation_id: Unique ID for this simulation
            total_time_seconds: Total simulation time
            timestep: Time between result saves (seconds)

        Returns:
            True if started successfully, False if already running
        """
        with self._lock:
            if simulation_id in self._running_simulations:
                return False

            stop_flag = threading.Event()
            self._stop_flags[simulation_id] = stop_flag

            thread = threading.Thread(
                target=self._run_simulation,
                args=(simulation_id, total_time_seconds, timestep, stop_flag),
                daemon=True
            )
            self._running_simulations[simulation_id] = thread
            thread.start()

            return True

    def stop_simulation(self, simulation_id: str) -> bool:
        """
        Stop a running simulation.

        Args:
            simulation_id: ID of simulation to stop

        Returns:
            True if stop signal sent, False if not running
        """
        with self._lock:
            if simulation_id not in self._stop_flags:
                return False

            self._stop_flags[simulation_id].set()
            return True

    def is_running(self, simulation_id: str) -> bool:
        """Check if a simulation is currently running."""
        with self._lock:
            if simulation_id not in self._running_simulations:
                return False
            return self._running_simulations[simulation_id].is_alive()

    def _run_simulation(
        self,
        simulation_id: str,
        total_time_seconds: int,
        timestep: float,
        stop_flag: threading.Event
    ):
        """
        Run simulation loop (called in background thread).

        Runs the simulation step by step, saving results to database
        after each timestep.
        """
        logger.info(f"Starting simulation {simulation_id} ({total_time_seconds}s)")
        try:
            # Update status to running
            database.update_simulation_status(simulation_id, "running")

            # Create simulation instance
            sim = simulation.create_simulation(total_time=float(total_time_seconds))

            current_time = 0.0

            # Save initial state
            fluxes = sim._calculate_fluxes(sim.metabolites)
            cell_metrics = sim._calculate_cell_metrics(sim.metabolites, current_time)

            database.save_result(
                simulation_id=simulation_id,
                time_seconds=current_time,
                metabolites=sim.metabolites,
                fluxes=fluxes,
                cell_metrics=cell_metrics
            )

            # Run simulation loop
            while current_time < total_time_seconds:
                # Check for stop signal
                if stop_flag.is_set():
                    database.update_simulation_status(
                        simulation_id,
                        "cancelled",
                        error_message="Simulation cancelled by user"
                    )
                    break

                # Run one timestep
                metabolites, fluxes, cell_metrics = sim.run_step(
                    current_time, dt=timestep
                )

                current_time += timestep

                # Save result to database
                database.save_result(
                    simulation_id=simulation_id,
                    time_seconds=current_time,
                    metabolites=metabolites,
                    fluxes=fluxes,
                    cell_metrics=cell_metrics
                )

                # Update simulation progress
                database.update_simulation_status(
                    simulation_id,
                    "running",
                    current_time_seconds=int(current_time)
                )

            else:
                # Completed normally
                database.update_simulation_status(simulation_id, "completed")
                logger.info(f"Simulation {simulation_id} completed successfully")

        except Exception as e:
            # Handle errors
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Simulation {simulation_id} failed: {e}")
            database.update_simulation_status(
                simulation_id,
                "failed",
                error_message=error_msg
            )

        finally:
            # Cleanup
            with self._lock:
                self._running_simulations.pop(simulation_id, None)
                self._stop_flags.pop(simulation_id, None)


# Global worker instance
_worker: Optional[SimulationWorker] = None


def get_worker() -> SimulationWorker:
    """Get or create the global worker instance."""
    global _worker
    if _worker is None:
        _worker = SimulationWorker()
    return _worker


def start_simulation(
    simulation_id: str,
    total_time_seconds: int = 3600,
    timestep: float = 1.0
) -> bool:
    """Start a simulation (convenience function)."""
    return get_worker().start_simulation(
        simulation_id, total_time_seconds, timestep
    )


def stop_simulation(simulation_id: str) -> bool:
    """Stop a simulation (convenience function)."""
    return get_worker().stop_simulation(simulation_id)


def is_running(simulation_id: str) -> bool:
    """Check if simulation is running (convenience function)."""
    return get_worker().is_running(simulation_id)
