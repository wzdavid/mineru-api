# Docker Configuration

This directory contains all Docker-related configuration files.

## Language

- [English](README.md) (Current)
- [中文](README.zh.md)

## File Description

- `Dockerfile.api` - API service image
- `Dockerfile.worker` - GPU Worker image (based on Dockerfile.base)
- `Dockerfile.worker.cpu` - CPU Worker image
- `Dockerfile.cleanup` - Cleanup service image
- `Dockerfile.base` - Base image (MinerU vLLM)
- `docker-compose.yml` - Docker Compose configuration

## Usage

### Quick Start

1. **Configure in `docker/.env`**:
   ```bash
   cd docker
   cp .env.example .env
   # Edit .env and set COMPOSE_PROFILES (e.g., mineru-cpu or mineru-gpu)
   ```

2. **Start all services**:
   ```bash
   cd docker && docker compose up -d
   ```

   Docker Compose will automatically read `COMPOSE_PROFILES` from `docker/.env` and start the appropriate services.

### Worker Selection

Configure worker type in `docker/.env`:

```bash
# Use CPU Worker (recommended for development)
COMPOSE_PROFILES=mineru-cpu

# Use GPU Worker (requires NVIDIA GPU)
COMPOSE_PROFILES=mineru-gpu

# Combine multiple profiles (e.g., with internal Redis)
COMPOSE_PROFILES=redis,mineru-cpu
```

### Manual Profile Selection

You can also manually specify profiles:

```bash
# Start with CPU Worker and internal Redis
cd docker && docker compose --profile redis --profile mineru-cpu up -d

# Start with GPU Worker (without internal Redis, using external Redis)
cd docker && docker compose --profile mineru-gpu up -d

# Start only API (no worker)
cd docker && docker compose up -d

# Start API with internal Redis (IMPORTANT: must use --profile redis)
cd docker && docker compose --profile redis up -d redis mineru-api

# Start API, Redis, and GPU Worker together
cd docker && docker compose --profile redis --profile mineru-gpu up -d redis mineru-api mineru-worker-gpu

# Start API, Redis, and CPU Worker together
cd docker && docker compose --profile redis --profile mineru-cpu up -d redis mineru-api mineru-worker-cpu
```

**Important Notes**:
- The `redis` service uses a profile, so you **must** use `--profile redis` when starting it
- The `mineru-worker-gpu` service uses `--profile mineru-gpu`
- The `mineru-worker-cpu` service uses `--profile mineru-cpu`
- You can combine multiple profiles: `--profile redis --profile mineru-gpu`
- If you see network errors, see the [Troubleshooting Network Issues](#troubleshooting-network-issues) section below

### View Logs and Stop Services

```bash
# View logs
cd docker && docker compose logs -f

# Stop services
cd docker && docker compose down
```

### Troubleshooting Network Issues

If you encounter network setup errors (e.g., "failed to set up container networking"):

**Step 1: Try simple restart first** (if containers were stopped cleanly):
```bash
cd docker
docker compose down
docker compose --profile redis up -d redis mineru-api
```

**Step 2: If simple restart fails, clean up manually**:
```bash
cd docker
# Stop and remove containers
docker compose down

# Force remove any remaining containers
docker rm -f mineru-api mineru-redis mineru-worker-gpu mineru-worker-cpu 2>/dev/null || true

# Remove networks (may have different names depending on project directory)
docker network rm docker_mineru-network 2>/dev/null || true
docker network rm mineru-api_mineru-network 2>/dev/null || true
docker network rm "$(basename "$(pwd)")_mineru-network" 2>/dev/null || true

# Check for any remaining mineru networks
docker network ls | grep mineru

# Restart with correct profiles
# For API + Redis only:
docker compose --profile redis up -d redis mineru-api

# For API + Redis + GPU Worker:
docker compose --profile redis --profile mineru-gpu up -d redis mineru-api mineru-worker-gpu

# For API + Redis + CPU Worker:
docker compose --profile redis --profile mineru-cpu up -d redis mineru-api mineru-worker-cpu
```

**Step 3: Check service status**:
```bash
docker compose ps
docker compose logs mineru-api
docker compose logs redis
```

**When to use manual cleanup**:
- Network exists but containers can't connect
- Containers are in an abnormal state (Exited, Dead, etc.)
- Simple `docker compose down` doesn't fully clean up
- You see persistent network errors even with correct `--profile` flags

For more troubleshooting information, see [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).

### Redis Configuration

#### Option 1: Use Internal Redis (Recommended for Development)

**Method 1: Using COMPOSE_PROFILES in `docker/.env`**:
```bash
# In docker/.env
COMPOSE_PROFILES=redis,mineru-cpu
```

Then start services:
```bash
cd docker && docker compose up -d
```

**Method 2: Using command line**:
```bash
cd docker && docker compose --profile redis up -d
```

Configure in `.env` (project root):
```bash
REDIS_URL=redis://redis:6379/0
```

#### Option 2: Use External Redis on Host Machine

If you have Redis running on your host machine or another container:

1. **Configure in `.env` (project root)**:
   ```bash
   # For Docker Desktop (Mac/Windows)
   REDIS_URL=redis://host.docker.internal:6379/0
   
   # For Linux, use host network or actual IP
   REDIS_URL=redis://172.17.0.1:6379/0
   # Or if Redis is on another machine
   REDIS_URL=redis://192.168.1.100:6379/0
   ```

2. **Configure in `docker/.env` (don't include redis profile)**:
   ```bash
   # Only include worker profile, not redis
   COMPOSE_PROFILES=mineru-cpu
   ```

3. **Start services**:
   ```bash
   cd docker && docker compose up -d
   ```

#### Option 3: Resolve Port Conflicts

If port 6379 is already in use by another Redis instance:

1. **Change Redis port in `docker/.env`**:
   ```bash
   REDIS_PORT=6380
   ```

2. **Update `REDIS_URL` in project root `.env`**:
   ```bash
   REDIS_URL=redis://redis:6379/0  # Internal port is still 6379
   # Or for external Redis on different port
   REDIS_URL=redis://host.docker.internal:6380/0
   ```

#### Redis with Authentication

If your external Redis requires authentication:

```bash
# With password only
REDIS_URL=redis://:password@host.docker.internal:6379/0

# With username and password
REDIS_URL=redis://username:password@host.docker.internal:6379/0
```

## Building Images

### Important: Build Order

The `mineru-worker-gpu` service depends on the base image `mineru-vllm:latest`, which must be built first.

**Option 1: Use the build script (Recommended)**

The build script automatically checks and builds the base image if needed:

```bash
# Build all images (automatically builds base image first)
cd docker && ./build.sh

# Build specific services
cd docker && ./build.sh --api
cd docker && ./build.sh --worker-gpu
cd docker && ./build.sh --worker-cpu
cd docker && ./build.sh --cleanup

# Build multiple services
cd docker && ./build.sh --api --worker-gpu
```

**Option 2: Manual build**

If you prefer to build manually:

```bash
# 1. First, build the base image
cd docker
docker build -f Dockerfile.base \
    --build-arg PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.org/simple} \
    -t mineru-vllm:latest ..

# 2. Then build other images
cd docker && docker compose build

# Or build specific services
cd docker && docker compose build mineru-api
cd docker && docker compose build mineru-worker-gpu  # Requires mineru-vllm:latest
cd docker && docker compose build mineru-worker-cpu
```

**Option 3: Using docker compose (will fail if base image missing)**

```bash
# This will fail if mineru-vllm:latest doesn't exist
cd docker && docker compose build mineru-worker-gpu
```

## Environment Variables

### Docker Build Configuration

For Docker build configuration (e.g., `PIP_INDEX_URL` for pip mirror), create a `.env` file in the `docker/` directory:

```bash
cd docker
cp .env.example .env
# Edit .env and set PIP_INDEX_URL to your preferred pip mirror
```

This `.env` file is used by Docker Compose for build arguments (e.g., `PIP_INDEX_URL`).

### Application Runtime Configuration

For application runtime configuration, ensure you have a `.env` file in the project root directory (copy from `.env.example` in the project root).

Docker Compose will automatically read the `../.env` file for runtime environment variables.

## Notes

- All Dockerfiles' build context is the project root directory (`..`)
- File paths are relative to the project root directory
- Volume mount paths are also relative to the project root directory
