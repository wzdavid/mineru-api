# Troubleshooting

This document lists common issues and solutions.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Task Execution Issues](#task-execution-issues)
- [Performance Issues](#performance-issues)
- [Storage Issues](#storage-issues)

## Connection Issues

### Redis Connection Failed

**Symptoms**: API or Worker cannot connect to Redis

**Solutions**:
1. Check if Redis service is running:
   ```bash
   cd docker && docker compose ps redis
   ```

2. Verify Redis connection address:
   - Docker Compose: `redis://redis:6379/0`
   - Local development: `redis://localhost:6379/0`

3. Check network connection:
   ```bash
   cd docker && docker compose exec mineru-api ping redis
   ```

4. View Redis logs:
   ```bash
   cd docker && docker compose logs redis
   ```

### API Not Accessible

**Symptoms**: Cannot access `http://localhost:8000`

**Solutions**:
1. Check API service status:
   ```bash
   cd docker && docker compose ps mineru-api
   ```

2. Check if port is occupied:
   ```bash
   lsof -i :8000
   ```

3. View API logs:
   ```bash
   cd docker && docker compose logs mineru-api
   ```

4. Check firewall settings

## Task Execution Issues

### Task Stuck in Pending State

**Symptoms**: Task status remains `pending` after submission

**Possible Causes**:
1. Worker not running
2. Worker not connected to correct queue
3. Redis connection issues

**Solutions**:
1. Check if Worker is running:
   ```bash
   cd docker && docker compose ps mineru-worker-cpu
   ```

2. Check Worker logs:
   ```bash
   cd docker && docker compose logs mineru-worker-cpu
   ```

3. Verify queue configuration:
   ```bash
   cd docker && docker compose exec mineru-worker-cpu env | grep MINERU_QUEUE
   ```

### Task Execution Failed

**Symptoms**: Task status is `failed`

**Solutions**:
1. View task error information:
   ```bash
   curl http://localhost:8000/api/v1/tasks/{task_id}
   ```

2. View Worker logs:
   ```bash
   cd docker && docker compose logs mineru-worker-cpu | grep ERROR
   ```

3. Check if file format is supported
4. Check if storage space is sufficient

### "daemonic processes are not allowed to have children"

**Symptoms**: Worker error, cannot execute tasks

**Cause**: MinerU internally uses `ProcessPoolExecutor`, while Celery's `prefork` pool child processes are daemon processes and cannot create child processes

**Solution**: **Must use `WORKER_POOL=threads`**

Verify configuration:
```bash
cd docker && docker compose exec mineru-worker-cpu env | grep WORKER_POOL
```

Should display: `WORKER_POOL=threads`

## Performance Issues

### Out of Memory (OOM Killed)

**Symptoms**: Container exit code 137

**Solutions**:
1. Increase Docker memory limit (Docker Desktop → Settings → Resources → Memory)
2. Reduce Worker concurrency: `WORKER_CONCURRENCY=1`
3. Limit container memory:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 4g
   ```
4. Check system memory: `docker stats`

### Slow Task Processing

**Solutions**:
1. Increase Worker count:
   ```bash
   cd docker && docker compose up -d --scale mineru-worker-cpu=4
   ```

2. Use GPU Worker (if GPU available):
   ```bash
   cd docker && docker compose --profile mineru-gpu up -d
   ```

3. Optimize Worker configuration:
   ```bash
   WORKER_CONCURRENCY=4
   WORKER_PREFETCH_MULTIPLIER=1
   ```

4. Check Redis performance

### Queue Backlog

**Symptoms**: Large number of pending tasks in queue

**Solutions**:
1. Increase Worker instances
2. Use priority queue for important tasks
3. Check if Worker is running normally
4. Consider using more powerful hardware

## Storage Issues

### File Upload Failed

**Symptoms**: Returns 413 error when uploading files

**Cause**: File size exceeds limit

**Solutions**:
1. Increase file size limit:
   ```bash
   MAX_FILE_SIZE=209715200  # 200MB
   ```

2. Check if file actually exceeds limit

### Insufficient Storage Space

**Symptoms**: Task fails, prompts insufficient storage space

**Solutions**:
1. Clean old files:
   ```bash
   cd docker && docker compose exec mineru-cleanup python cleanup/cleanup_outputs.py
   ```

2. Configure automatic cleanup:
   ```bash
   cd docker && docker compose --profile mineru-cleanup up -d
   ```

3. Increase storage space or use S3 storage

### S3 Connection Issues

**Symptoms**: Connection failed when using S3 storage

**Solutions**:
1. Verify S3 configuration:
   ```bash
   cd docker && docker compose exec mineru-api env | grep MINERU_S3
   ```

2. Check if S3 service is accessible:
   ```bash
   curl http://minio:9000
   ```

3. Verify access key and secret key are correct
4. Check network connection and firewall

## Viewing Logs

### View All Service Logs

```bash
cd docker && docker compose logs -f
```

### View Specific Service Logs

```bash
# API logs
cd docker && docker compose logs -f mineru-api

# Worker logs
cd docker && docker compose logs -f mineru-worker-cpu

# Redis logs
cd docker && docker compose logs -f redis
```

### View Error Logs

```bash
cd docker && docker compose logs | grep -i error
cd docker && docker compose logs mineru-worker-cpu | grep -i error
```

## Debugging Tips

### Enter Container for Debugging

```bash
# Enter API container
cd docker && docker compose exec mineru-api bash

# Enter Worker container
cd docker && docker compose exec mineru-worker-cpu bash
```

### Check Environment Variables

```bash
# Check API environment variables
cd docker && docker compose exec mineru-api env

# Check Worker environment variables
cd docker && docker compose exec mineru-worker-cpu env
```

### Test Redis Connection

```bash
cd docker && docker compose exec mineru-api python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### Test Storage Connection

```bash
# Test local storage
cd docker && docker compose exec mineru-api ls -la /tmp/mineru_temp

# Test S3 storage (inside container)
cd docker && docker compose exec mineru-api python -c "from shared.storage import get_storage; s = get_storage(); print(s.storage_type)"
```

## Getting Help

If the above solutions cannot resolve the issue:

1. View complete logs: `cd docker && docker compose logs > logs.txt`
2. Check system resources: `docker stats`
3. View GitHub Issues: [Issues](https://github.com/wzdavid/mineru-api/issues)
4. Submit a new Issue, including:
   - Error information
   - Log output
   - Configuration information (hide sensitive information)
   - Reproduction steps

## More Information

- [Deployment Guide](DEPLOYMENT.md)
- [Configuration Reference](CONFIGURATION.md)
- [Storage Configuration](S3_STORAGE.md)
