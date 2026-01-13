# Multi-stage build for minimal cell simulation API
FROM python:3.7-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    cmake \
    git \
    wget \
    libblas-dev \
    liblapack-dev \
    libsundials-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the odecell package and install it
COPY odecell/ /build/odecell/
WORKDIR /build/odecell
RUN pip install --no-cache-dir .

# Final stage - runtime
FROM python:3.7-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libblas3 \
    liblapack3 \
    libsundials-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ /app/
COPY CME_ODE/ /app/CME_ODE/
COPY RDME_gCME_ODE/ /app/RDME_gCME_ODE/

# Create directories for simulation outputs
RUN mkdir -p /app/simulations /app/outputs

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH \
    PORT=8080

# Expose port
EXPOSE 8080

# Run the API server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
