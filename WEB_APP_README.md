# Minimal Cell Model - Web Application

An interactive web interface for running and visualizing minimal cell model simulations.

## Features

- **Web-based Interface**: Run simulations from any browser, no local setup required
- **Real-time Monitoring**: Track simulation progress and status
- **Configurable Parameters**: Adjust simulation time, restart intervals, and other parameters
- **Cloud Deployment**: Deployed on Railway for easy access and automatic scaling
- **RESTful API**: FastAPI backend for programmatic access to simulations

## Quick Start

### Access the Deployed Application

Once deployed to Railway, access your application at:
- Frontend: `https://your-frontend-url.up.railway.app`
- API Docs: `https://your-backend-url.up.railway.app/docs`

### Run Locally

Using Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8080
# API Docs: http://localhost:8080/docs
```

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  React Frontend │────────▶│  FastAPI Backend│
│   (Port 3000)   │  HTTP   │   (Port 8080)   │
└─────────────────┘         └─────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   CME-ODE       │
                            │   Simulation    │
                            │   Engine        │
                            └─────────────────┘
```

## API Endpoints

### Health Check
```
GET /health
```

### Start Simulation
```
POST /simulations
{
  "simulation_time": 125.0,
  "restart_interval": 1.0,
  "simulation_type": "cme-ode",
  "random_seed": 42
}
```

### Get Simulation Status
```
GET /simulations/{simulation_id}
```

### List All Simulations
```
GET /simulations?status=completed&limit=50
```

### Get Simulation Results
```
GET /simulations/{simulation_id}/results
```

### Delete Simulation
```
DELETE /simulations/{simulation_id}
```

## Development

### Backend Development

```bash
# Install dependencies
pip install -r backend/requirements.txt
pip install -e odecell/

# Run development server
cd backend
python main.py

# API will be available at http://localhost:8080
# Interactive docs at http://localhost:8080/docs
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm start

# App will be available at http://localhost:3000
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

**Quick deployment to Railway:**

1. Push code to GitHub
2. Connect repository to Railway
3. Create two services (backend + frontend)
4. Configure environment variables
5. Deploy automatically on every commit

## Simulation Parameters

### Simulation Time
- **Range**: 1-500 minutes
- **Default**: 125 minutes (one full cell cycle)
- **Description**: Total time to simulate

### Restart Interval
- **Range**: 0.1-10 minutes
- **Default**: 1 minute
- **Description**: Frequency of metabolite pool updates to gene expression rates

### Simulation Type
- **CME-ODE**: Well-stirred chemical master equation model (default)
- **RDME**: Spatially-resolved reaction-diffusion model (coming soon)

### Random Seed
- **Optional**: Leave empty for non-deterministic simulations
- **Description**: Set a seed for reproducible results

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation
- **NumPy/SciPy**: Scientific computing
- **COBRApy**: Metabolic modeling
- **pycvodes**: ODE solver

### Frontend
- **React 18**: UI framework
- **Axios**: HTTP client
- **Recharts**: Data visualization (planned)
- **Nginx**: Production web server

### Infrastructure
- **Docker**: Containerization
- **Railway**: Hosting platform
- **GitHub Actions**: CI/CD (optional)

## Project Structure

```
Minimal_Cell/
├── backend/                  # FastAPI backend
│   ├── main.py              # API endpoints
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container
├── frontend/                # React frontend
│   ├── src/
│   │   ├── App.js          # Main application
│   │   └── App.css         # Styles
│   ├── package.json        # Node dependencies
│   ├── nginx.conf          # Production web server config
│   └── Dockerfile          # Frontend container
├── CME_ODE/                 # Simulation engine
├── RDME_gCME_ODE/          # Spatial simulation (coming soon)
├── odecell/                # Python package for ODE models
├── docker-compose.yml      # Local development setup
├── railway.json            # Railway configuration
└── DEPLOYMENT.md           # Deployment guide
```

## Roadmap

### Completed
- ✅ FastAPI backend with simulation endpoints
- ✅ React frontend with parameter configuration
- ✅ Docker containerization
- ✅ Railway deployment configuration
- ✅ Auto-deployment on git push

### In Progress
- 🔄 Integration with actual CME-ODE simulation engine
- 🔄 Result visualization and plotting
- 🔄 Simulation result storage

### Planned
- ⏳ RDME spatial simulation support
- ⏳ User authentication
- ⏳ PostgreSQL database for persistent storage
- ⏳ Advanced parameter customization
- ⏳ Batch simulation runs
- ⏳ Export results to CSV/JSON
- ⏳ Real-time progress updates via WebSockets
- ⏳ Comparison of multiple simulations
- ⏳ Preset parameter configurations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

```bash
# Backend tests (to be implemented)
cd backend
pytest

# Frontend tests (to be implemented)
cd frontend
npm test
```

## License

This project uses the Minimal Cell Model which is licensed under GPLv3. See the original repository for details.

## Acknowledgments

- Original Minimal Cell Model: https://github.com/zanert2/Minimal_Cell
- Built with FastAPI, React, and Railway
- Deployed as part of a computational systems biology project

## Support

For issues and questions:
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment help
- Review API docs at `/docs` endpoint
- Open an issue on GitHub

## Performance Notes

- First simulation may take longer as the system initializes
- Services auto-sleep after 10 minutes of inactivity (Railway)
- Cold start time: ~10-30 seconds
- Typical simulation time: 1-10 minutes depending on parameters
