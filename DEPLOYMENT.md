# Railway Deployment

## Setup Steps

### 1. Push to GitHub
```bash
git push origin main
```

### 2. Railway Account
- Go to https://railway.app
- Sign in with GitHub

### 3. Create Project
- Click "New Project" → "Deploy from GitHub repo"
- Select your repository

### 4. Backend Service
- Name: `backend`
- Root Directory: `backend`
- Environment Variables:
  ```
  PORT=8080
  PYTHONUNBUFFERED=1
  ```
- Deploy and copy the URL

### 5. Frontend Service
- Click "New Service" → Select same repo
- Name: `frontend`
- Root Directory: `frontend`
- Environment Variable:
  ```
  REACT_APP_API_URL=<your-backend-url>
  ```
- Deploy

### 6. Access
- Frontend: Railway provides a URL for the frontend service
- API: `<backend-url>/docs` for API documentation

## Local Testing
```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend: http://localhost:8080
```

## Auto-Deployment
Every push to main automatically deploys both services.
