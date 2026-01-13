import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Get API URL from environment variable or default to localhost
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function App() {
  const [simulations, setSimulations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Form state
  const [simulationTime, setSimulationTime] = useState(125.0);
  const [restartInterval, setRestartInterval] = useState(1.0);
  const [simulationType, setSimulationType] = useState('cme-ode');
  const [randomSeed, setRandomSeed] = useState('');

  // Fetch simulations list
  const fetchSimulations = async () => {
    try {
      const response = await axios.get(`${API_URL}/simulations`);
      setSimulations(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching simulations:', err);
      setError('Failed to fetch simulations');
    }
  };

  // Load simulations on mount and refresh every 5 seconds
  useEffect(() => {
    fetchSimulations();
    const interval = setInterval(fetchSimulations, 5000);
    return () => clearInterval(interval);
  }, []);

  // Start a new simulation
  const startSimulation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        simulation_time: parseFloat(simulationTime),
        restart_interval: parseFloat(restartInterval),
        simulation_type: simulationType,
        random_seed: randomSeed ? parseInt(randomSeed) : null,
      };

      const response = await axios.post(`${API_URL}/simulations`, payload);
      console.log('Simulation started:', response.data);

      // Refresh simulations list
      await fetchSimulations();

      alert(`Simulation started! ID: ${response.data.simulation_id}`);
    } catch (err) {
      console.error('Error starting simulation:', err);
      setError(err.response?.data?.detail || 'Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  // Delete a simulation
  const deleteSimulation = async (simulationId) => {
    if (!window.confirm('Are you sure you want to delete this simulation?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/simulations/${simulationId}`);
      await fetchSimulations();
    } catch (err) {
      console.error('Error deleting simulation:', err);
      setError('Failed to delete simulation');
    }
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return '#4CAF50';
      case 'running':
        return '#2196F3';
      case 'failed':
        return '#f44336';
      case 'pending':
        return '#FF9800';
      default:
        return '#9E9E9E';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Minimal Cell Model Simulation</h1>
        <p>Interactive simulation interface for computational cell biology</p>
      </header>

      <div className="container">
        {/* Simulation Form */}
        <div className="card">
          <h2>Start New Simulation</h2>
          {error && <div className="error-message">{error}</div>}

          <form onSubmit={startSimulation}>
            <div className="form-group">
              <label htmlFor="simulationType">Simulation Type:</label>
              <select
                id="simulationType"
                value={simulationType}
                onChange={(e) => setSimulationType(e.target.value)}
                disabled={loading}
              >
                <option value="cme-ode">CME-ODE (Well-stirred)</option>
                <option value="rdme">RDME (Spatial - Not yet implemented)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="simulationTime">
                Simulation Time (minutes): {simulationTime}
              </label>
              <input
                type="range"
                id="simulationTime"
                min="1"
                max="500"
                step="1"
                value={simulationTime}
                onChange={(e) => setSimulationTime(e.target.value)}
                disabled={loading}
              />
              <input
                type="number"
                value={simulationTime}
                onChange={(e) => setSimulationTime(e.target.value)}
                min="1"
                max="500"
                step="0.1"
                disabled={loading}
                style={{ width: '100px', marginLeft: '10px' }}
              />
            </div>

            <div className="form-group">
              <label htmlFor="restartInterval">
                Restart Interval (minutes): {restartInterval}
              </label>
              <input
                type="range"
                id="restartInterval"
                min="0.1"
                max="10"
                step="0.1"
                value={restartInterval}
                onChange={(e) => setRestartInterval(e.target.value)}
                disabled={loading}
              />
              <input
                type="number"
                value={restartInterval}
                onChange={(e) => setRestartInterval(e.target.value)}
                min="0.1"
                max="10"
                step="0.1"
                disabled={loading}
                style={{ width: '100px', marginLeft: '10px' }}
              />
            </div>

            <div className="form-group">
              <label htmlFor="randomSeed">Random Seed (optional):</label>
              <input
                type="number"
                id="randomSeed"
                value={randomSeed}
                onChange={(e) => setRandomSeed(e.target.value)}
                placeholder="Leave empty for random"
                disabled={loading}
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Starting...' : 'Start Simulation'}
            </button>
          </form>
        </div>

        {/* Simulations List */}
        <div className="card">
          <h2>Simulations ({simulations.length})</h2>

          {simulations.length === 0 ? (
            <p className="no-simulations">No simulations yet. Start one above!</p>
          ) : (
            <div className="simulations-list">
              {simulations.map((sim) => (
                <div key={sim.simulation_id} className="simulation-item">
                  <div className="simulation-header">
                    <h3>
                      <span
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(sim.status) }}
                      />
                      {sim.simulation_type.toUpperCase()}
                    </h3>
                    <span className="simulation-status">{sim.status}</span>
                  </div>

                  <div className="simulation-details">
                    <p><strong>ID:</strong> {sim.simulation_id.substring(0, 8)}...</p>
                    <p><strong>Created:</strong> {new Date(sim.created_at).toLocaleString()}</p>

                    {sim.progress_percent !== null && sim.status === 'running' && (
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${sim.progress_percent}%` }}
                        />
                        <span className="progress-text">{sim.progress_percent.toFixed(0)}%</span>
                      </div>
                    )}

                    {sim.error_message && (
                      <p className="error-text"><strong>Error:</strong> {sim.error_message}</p>
                    )}

                    {sim.completed_at && (
                      <p><strong>Completed:</strong> {new Date(sim.completed_at).toLocaleString()}</p>
                    )}
                  </div>

                  <div className="simulation-actions">
                    {sim.status === 'completed' && (
                      <button
                        className="btn-secondary"
                        onClick={() => window.open(`${API_URL}/simulations/${sim.simulation_id}/results`, '_blank')}
                      >
                        View Results
                      </button>
                    )}
                    <button
                      className="btn-danger"
                      onClick={() => deleteSimulation(sim.simulation_id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <footer className="App-footer">
        <p>Minimal Cell Model - Computational Systems Biology</p>
      </footer>
    </div>
  );
}

export default App;
