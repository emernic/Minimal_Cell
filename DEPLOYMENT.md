# Minimal Cell Model - Deployment Guide

This guide will walk you through deploying the Minimal Cell Model web application to Railway.

## Overview

The application consists of two services:
1. **Backend API** - FastAPI server that runs cell simulations
2. **Frontend** - React web interface for configuring and monitoring simulations

## Prerequisites

- GitHub account (to host the repository)
- Railway account (sign up at https://railway.app)
- Git installed locally

## Project Structure

```
Minimal_Cell/
├── backend/
│   ├── Dockerfile              # Backend container definition
│   ├── requirements.txt        # Python dependencies
│   └── main.py                 # FastAPI application
├── frontend/
│   ├── Dockerfile              # Frontend container definition
│   ├── nginx.conf              # Nginx configuration
│   ├── package.json            # Node dependencies
│   └── src/                    # React application source
├── docker-compose.yml          # Local development setup
├── railway.json                # Railway configuration
└── DEPLOYMENT.md               # This file
```

## Deployment Steps

### Step 1: Push Your Code to GitHub

If you haven't already, push this repository to GitHub:

```bash
# Add all the new files
git add backend/ frontend/ docker-compose.yml railway.json .railwayignore DEPLOYMENT.md

# Commit the changes
git commit -m "Add web application with Railway deployment setup"

# Push to your repository
git push origin main
```

### Step 2: Sign Up for Railway

1. Go to https://railway.app
2. Click "Login" and sign in with your GitHub account
3. Authorize Railway to access your GitHub repositories

### Step 3: Create a New Project

1. Click "New Project" in your Railway dashboard
2. Select "Deploy from GitHub repo"
3. Choose your `Minimal_Cell` repository
4. Railway will detect your repository and prepare for deployment

### Step 4: Set Up the Backend Service

1. Railway will create an initial service. Configure it as the backend:
   - **Name**: Set the service name to `backend`
   - **Root Directory**: Set to `backend` (this tells Railway where the Dockerfile is)
   - **Dockerfile Path**: Should auto-detect as `backend/Dockerfile`

2. Configure environment variables for the backend:
   - Click on the backend service
   - Go to "Variables" tab
   - Add the following variables:
     ```
     PORT=8080
     PYTHONUNBUFFERED=1
     ```

3. Click "Deploy" and wait for the build to complete (may take 5-10 minutes for first build)

4. Once deployed, Railway will provide a public URL for your backend (e.g., `https://backend-production-xxxx.up.railway.app`)
   - Copy this URL, you'll need it for the frontend

### Step 5: Set Up the Frontend Service

1. In your Railway project, click "New Service"
2. Select "GitHub Repo" and choose the same repository
3. Configure the frontend service:
   - **Name**: Set to `frontend`
   - **Root Directory**: Set to `frontend`
   - **Dockerfile Path**: Should auto-detect as `frontend/Dockerfile`

4. Configure environment variables for the frontend:
   - Go to "Variables" tab
   - Add:
     ```
     REACT_APP_API_URL=https://your-backend-url.up.railway.app
     ```
     Replace `your-backend-url` with the actual backend URL from Step 4

5. Click "Deploy"

### Step 6: Configure Auto-Deployment

Railway automatically sets up auto-deployment from your GitHub repository:

1. Every push to your `main` branch will trigger a new deployment
2. You can see deployment logs in the Railway dashboard
3. Each service deploys independently

To verify auto-deployment is working:
- Make a small change to your code
- Push to `main` branch
- Watch the deployment in Railway dashboard

### Step 7: Access Your Application

Once both services are deployed:

1. Get the frontend URL from Railway dashboard (e.g., `https://frontend-production-xxxx.up.railway.app`)
2. Open it in your browser
3. You should see the Minimal Cell Simulation interface
4. Try starting a simulation to verify everything works

## Local Development

To run the application locally for testing:

```bash
# Using Docker Compose (recommended)
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8080
# API Docs: http://localhost:8080/docs
```

For frontend development without Docker:

```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000
```

For backend development without Docker:

```bash
cd backend
pip install -r requirements.txt
cd ..
pip install -e odecell/
python backend/main.py
# Runs on http://localhost:8080
```

## Environment Variables Reference

### Backend Service
- `PORT` - Port the API server listens on (default: 8080)
- `PYTHONUNBUFFERED` - Ensures Python output is logged immediately

### Frontend Service
- `REACT_APP_API_URL` - URL of the backend API service

## Troubleshooting

### Backend build fails

**Issue**: Python dependencies fail to install

**Solution**:
- Check that `libsundials-dev` is available in the Dockerfile
- Verify all Python packages in `requirements.txt` are compatible with Python 3.7
- Check build logs in Railway dashboard for specific error messages

### Frontend can't connect to backend

**Issue**: API requests fail with CORS errors

**Solution**:
- Verify `REACT_APP_API_URL` environment variable is set correctly in frontend service
- Check that backend service is running and accessible
- Ensure CORS middleware is configured in `backend/main.py`

### Simulations fail to run

**Issue**: Simulations start but fail during execution

**Solution**:
- Check backend logs in Railway dashboard
- Verify simulation parameters are within valid ranges
- Ensure sufficient memory is allocated to backend service (increase in Railway settings if needed)

### Builds are slow

**Issue**: Each deployment takes 10+ minutes

**Solution**:
- Railway caches Docker layers, so subsequent builds should be faster
- First build is always slower due to installing all dependencies
- Consider using Railway's build cache settings

## Monitoring and Logs

Railway provides built-in monitoring:

1. **Deployment Logs**: View build and runtime logs for each service
2. **Metrics**: CPU, memory, and network usage
3. **Health Checks**: Automatic health monitoring

To view logs:
- Click on a service in Railway dashboard
- Go to "Deployments" tab
- Click on a deployment to see logs

## Estimated Costs

Railway pricing (as of 2026):
- **Hobby Plan**: $5/month base + usage-based pricing
- **Compute**: ~$20/vCPU-month, ~$10/GB RAM-month
- **For this project**: Expect $10-20/month for light use with auto-sleep enabled

Tips to minimize costs:
- Services auto-sleep after 10 minutes of inactivity (no compute charges while sleeping)
- Use Railway's usage dashboard to monitor costs
- Delete old simulation results to save storage costs

## Scaling

As your usage grows:

1. **Increase resources**: Adjust CPU/RAM in Railway service settings
2. **Add replicas**: Enable multiple instances for high availability
3. **Add database**: Deploy PostgreSQL to persist simulation results
4. **Add caching**: Use Redis for faster repeated queries

## Next Steps

Now that you have a working deployment:

1. **Customize the UI**: Modify `frontend/src/App.js` to add features
2. **Implement actual simulations**: Update `backend/main.py` to run real CME-ODE simulations
3. **Add authentication**: Protect your app with user logins
4. **Add database**: Store simulation results in PostgreSQL
5. **Add result visualization**: Use Plotly or Recharts to display simulation data

## Support

- Railway docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Report issues: https://github.com/YOUR_USERNAME/Minimal_Cell/issues

## Security Notes

- Never commit API keys or secrets to the repository
- Use Railway's environment variables for sensitive configuration
- Enable Railway's built-in DDoS protection for production use
- Consider adding rate limiting to the API
