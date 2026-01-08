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
```

### View Logs and Stop Services

```bash
# View logs
cd docker && docker compose logs -f

# Stop services
cd docker && docker compose down
```

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

```bash
# Build all images
cd docker && docker compose build

# Build specific service
cd docker && docker compose build mineru-api
cd docker && docker compose build mineru-worker-cpu
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
