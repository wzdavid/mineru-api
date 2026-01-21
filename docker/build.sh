#!/bin/bash
# Build script for MinerU Docker images
# This script ensures base images are built before dependent images

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get project root directory (parent of docker/)
PROJECT_ROOT="$(cd .. && pwd)"

echo "=== MinerU Docker Build Script ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if base image exists
if ! docker image inspect mineru-vllm:latest > /dev/null 2>&1; then
    echo "Base image 'mineru-vllm:latest' not found. Building it first..."
    echo ""
    echo "Building base image from Dockerfile.base..."
    cd "$PROJECT_ROOT"
    docker build -f docker/Dockerfile.base \
        --build-arg PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.org/simple} \
        -t mineru-vllm:latest .
    echo ""
    echo "✓ Base image 'mineru-vllm:latest' built successfully"
    echo ""
else
    echo "✓ Base image 'mineru-vllm:latest' already exists"
    echo ""
fi

# Return to docker directory
cd "$SCRIPT_DIR"

# Parse command line arguments
BUILD_ALL=false
BUILD_API=false
BUILD_WORKER_GPU=false
BUILD_WORKER_CPU=false
BUILD_CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all|-a)
            BUILD_ALL=true
            shift
            ;;
        --api)
            BUILD_API=true
            shift
            ;;
        --worker-gpu|--gpu)
            BUILD_WORKER_GPU=true
            shift
            ;;
        --worker-cpu|--cpu)
            BUILD_WORKER_CPU=true
            shift
            ;;
        --cleanup)
            BUILD_CLEANUP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--all|--api|--worker-gpu|--worker-cpu|--cleanup]"
            exit 1
            ;;
    esac
done

# If no specific service is specified, build all
if [ "$BUILD_ALL" = false ] && [ "$BUILD_API" = false ] && [ "$BUILD_WORKER_GPU" = false ] && [ "$BUILD_WORKER_CPU" = false ] && [ "$BUILD_CLEANUP" = false ]; then
    BUILD_ALL=true
fi

echo "Building services..."
echo ""

if [ "$BUILD_ALL" = true ] || [ "$BUILD_API" = true ]; then
    echo "Building mineru-api..."
    docker compose build mineru-api
    echo "✓ mineru-api built"
    echo ""
fi

if [ "$BUILD_ALL" = true ] || [ "$BUILD_WORKER_GPU" = true ]; then
    echo "Building mineru-worker-gpu (requires base image mineru-vllm:latest)..."
    docker compose build mineru-worker-gpu
    echo "✓ mineru-worker-gpu built"
    echo ""
fi

if [ "$BUILD_ALL" = true ] || [ "$BUILD_WORKER_CPU" = true ]; then
    echo "Building mineru-worker-cpu..."
    docker compose build mineru-worker-cpu
    echo "✓ mineru-worker-cpu built"
    echo ""
fi

if [ "$BUILD_ALL" = true ] || [ "$BUILD_CLEANUP" = true ]; then
    echo "Building mineru-cleanup..."
    docker compose build mineru-cleanup
    echo "✓ mineru-cleanup built"
    echo ""
fi

echo "=== Build Complete ==="
echo ""
echo "Built images:"
docker images | grep -E "mineru|REPOSITORY" | head -10
