FROM python:3.7-slim as builder

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

WORKDIR /build

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY odecell/ /build/odecell/
WORKDIR /build/odecell
RUN pip install --no-cache-dir .

FROM python:3.7-slim

RUN apt-get update && apt-get install -y \
    libblas3 \
    liblapack3 \
    libsundials-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY backend/ /app/
COPY CME_ODE/ /app/CME_ODE/
COPY RDME_gCME_ODE/ /app/RDME_gCME_ODE/

RUN mkdir -p /app/simulations /app/outputs

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH \
    PORT=8080

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
