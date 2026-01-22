# 故障排除

本文档列出常见问题和解决方案。

## 目录

- [Docker 网络问题](#docker-网络问题)
- [连接问题](#连接问题)
- [任务执行问题](#任务执行问题)
- [性能问题](#性能问题)
- [存储问题](#存储问题)

## Docker 构建问题

### 构建 Worker 时找不到基础镜像

**症状**: 构建 `mineru-worker-gpu` 时出错："failed to solve: failed to fetch ... mineru-vllm:latest"

**原因**: `mineru-worker-gpu` 服务依赖于基础镜像 `mineru-vllm:latest`，必须先构建该基础镜像。

**解决方案**:

1. **使用构建脚本（推荐）**:
   ```bash
   cd docker && sh build.sh --worker-gpu
   ```
   脚本会自动检查并在需要时构建基础镜像。

2. **手动先构建基础镜像**:
   ```bash
   cd docker
   docker build -f Dockerfile.base \
       --build-arg PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.org/simple} \
       -t mineru-vllm:latest ..
   
   # 然后构建 worker
   docker compose build mineru-worker-gpu
   ```

3. **使用脚本构建所有镜像**:
   ```bash
   cd docker && sh build.sh
   ```

### 基础镜像构建失败

**症状**: 构建 `mineru-vllm:latest` 基础镜像时出错

**可能原因**:
1. 下载模型时网络问题
2. 磁盘空间不足
3. Docker 构建上下文问题

**解决方案**:
1. 检查网络连接和 pip 镜像源配置
2. 检查可用磁盘空间：`df -h`
3. 确保从正确的目录运行构建命令：
   ```bash
   # 从 docker/ 目录
   docker build -f Dockerfile.base -t mineru-vllm:latest ..
   ```
4. 检查构建日志以获取具体错误信息
5. 如果有缓存问题，尝试使用 `--no-cache` 构建：
   ```bash
   docker build --no-cache -f docker/Dockerfile.base -t mineru-vllm:latest .
   ```

## Docker 网络问题

### 容器网络设置失败

**症状**: 启动服务时出现类似 "failed to set up container networking: network ... not found" 或类似的网络错误

**可能原因**:
1. 现有网络处于异常状态
2. 容器名称冲突
3. 之前运行未完全清理
4. Docker 网络驱动问题

**解决方案**:

1. **清理现有容器和网络**:
   ```bash
   cd docker
   # 停止并删除所有容器
   docker compose down
   
   # 删除特定网络（如果存在）
   docker network rm docker_mineru-network 2>/dev/null || true
   docker network rm mineru-api_mineru-network 2>/dev/null || true
   
   # 删除任何孤立的容器
   docker rm -f mineru-api mineru-redis mineru-worker-gpu mineru-worker-cpu 2>/dev/null || true
   ```

2. **检查网络冲突**:
   ```bash
   # 列出所有网络
   docker network ls
   
   # 检查现有网络（如果找到）
   docker network inspect docker_mineru-network
   ```

3. **清理所有 Docker 资源**（如果上述方法不起作用）:
   ```bash
   cd docker
   docker compose down -v  # 同时删除卷
   docker system prune -f  # 清理未使用的资源
   ```

4. **重启 Docker 守护进程**（如果在 Linux 上）:
   ```bash
   sudo systemctl restart docker
   ```

5. **重建并启动服务**:
   ```bash
   cd docker
   # 仅启动 API + Redis：
   docker compose --profile redis up -d --build redis mineru-api
   
   # 启动 API + Redis + GPU Worker：
   docker compose --profile redis --profile mineru-gpu up -d --build redis mineru-api mineru-worker-gpu
   
   # 启动 API + Redis + CPU Worker：
   docker compose --profile redis --profile mineru-cpu up -d --build redis mineru-api mineru-worker-cpu
   ```

6. **如果使用 profiles，确保使用正确的命令**:
   ```bash
   cd docker
   # 仅启动 API + Redis：
   docker compose --profile redis up -d redis mineru-api
   
   # 启动 API + Redis + GPU Worker：
   docker compose --profile redis --profile mineru-gpu up -d redis mineru-api mineru-worker-gpu
   
   # 启动 API + Redis + CPU Worker：
   docker compose --profile redis --profile mineru-cpu up -d redis mineru-api mineru-worker-cpu
   ```

### 网络名称冲突

**症状**: 网络创建失败，提示 "network already exists" 错误

**解决方案**:
1. 删除冲突的网络:
   ```bash
   docker network rm docker_mineru-network
   # 或如果使用不同的项目名称
   docker network rm <项目名称>_mineru-network
   ```

2. 在 `docker-compose.yml` 中使用不同的网络名称:
   ```yaml
   networks:
     mineru-network:
       name: mineru-custom-network
       driver: bridge
   ```

## 连接问题

### Redis 连接失败

**症状**: API 或 Worker 无法连接到 Redis

**解决方案**:
1. 检查 Redis 服务是否运行:
   ```bash
   docker compose ps redis
   ```

2. 验证 Redis 连接地址:
   - Docker Compose: `redis://redis:6379/0`
   - 本地开发: `redis://localhost:6379/0`

3. 检查网络连接:
   ```bash
   docker compose exec mineru-api ping redis
   ```

4. 查看 Redis 日志:
   ```bash
   docker compose logs redis
   ```

### API 无法访问

**症状**: 无法访问 `http://localhost:8000`

**解决方案**:
1. 检查 API 服务状态:
   ```bash
   docker compose ps mineru-api
   ```

2. 检查端口是否被占用:
   ```bash
   lsof -i :8000
   ```

3. 查看 API 日志:
   ```bash
   docker compose logs mineru-api
   ```

4. 检查防火墙设置

## 任务执行问题

### 任务一直处于 pending 状态

**症状**: 提交任务后，任务状态一直是 `pending`

**可能原因**:
1. Worker 未运行
2. Worker 未连接到正确的队列
3. Redis 连接问题

**解决方案**:
1. 检查 Worker 是否运行:
   ```bash
   docker compose ps mineru-worker-cpu
   ```

2. 检查 Worker 日志:
   ```bash
   docker compose logs mineru-worker-cpu
   ```

3. 验证队列配置:
   ```bash
   docker compose exec mineru-worker-cpu env | grep MINERU_QUEUE
   ```

### 任务执行失败

**症状**: 任务状态为 `failed`

**解决方案**:
1. 查看任务错误信息:
   ```bash
   curl http://localhost:8000/api/v1/tasks/{task_id}
   ```

2. 查看 Worker 日志:
   ```bash
   docker compose logs mineru-worker-cpu | grep ERROR
   ```

3. 检查文件格式是否支持
4. 检查存储空间是否充足

### "daemonic processes are not allowed to have children"

**症状**: Worker 报错，无法执行任务

**原因**: MinerU 内部使用 `ProcessPoolExecutor`，而 Celery 的 `prefork` 池子进程是 daemon，无法创建子进程

**解决方案**: **必须使用 `WORKER_POOL=threads`**

验证配置:
```bash
docker compose exec mineru-worker-cpu env | grep WORKER_POOL
```

应该显示: `WORKER_POOL=threads`

## 性能问题

### 内存不足（OOM Killed）

**症状**: 容器退出码 137

**解决方案**:
1. 增加 Docker 内存限制（Docker Desktop → Settings → Resources → Memory）
2. 减少 Worker 并发数: `WORKER_CONCURRENCY=1`
3. 限制容器内存:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 4g
   ```
4. 检查系统内存: `docker stats`

### 任务处理缓慢

**解决方案**:
1. 增加 Worker 数量:
   ```bash
   docker compose up -d --scale mineru-worker-cpu=4
   ```

2. 使用 GPU Worker（如果有 GPU）:
   ```bash
   docker compose --profile mineru-gpu up -d
   ```

3. 优化 Worker 配置:
   ```bash
   WORKER_CONCURRENCY=4
   WORKER_PREFETCH_MULTIPLIER=1
   ```

4. 检查 Redis 性能

### 队列堆积

**症状**: 队列中有大量待处理任务

**解决方案**:
1. 增加 Worker 实例
2. 使用优先级队列处理重要任务
3. 检查 Worker 是否正常运行
4. 考虑使用更强大的硬件

## 存储问题

### 文件上传失败

**症状**: 上传文件时返回 413 错误

**原因**: 文件大小超过限制

**解决方案**:
1. 增加文件大小限制:
   ```bash
   MAX_FILE_SIZE=209715200  # 200MB
   ```

2. 检查文件是否真的超过限制

### 存储空间不足

**症状**: 任务失败，提示存储空间不足

**解决方案**:
1. 清理旧文件:
   ```bash
   docker compose exec mineru-cleanup python cleanup/cleanup_outputs.py
   ```

2. 配置自动清理:
   ```bash
   docker compose --profile mineru-cleanup up -d
   ```

3. 增加存储空间或使用 S3 存储

### S3 连接问题

**症状**: 使用 S3 存储时连接失败

**解决方案**:
1. 验证 S3 配置:
   ```bash
   docker compose exec mineru-api env | grep MINERU_S3
   ```

2. 检查 S3 服务是否可访问:
   ```bash
   curl http://minio:9000
   ```

3. 验证访问密钥和密钥是否正确
4. 检查网络连接和防火墙

## 日志查看

### 查看所有服务日志

```bash
docker compose logs -f
```

### 查看特定服务日志

```bash
# API 日志
docker compose logs -f mineru-api

# Worker 日志
docker compose logs -f mineru-worker-cpu

# Redis 日志
docker compose logs -f redis
```

### 查看错误日志

```bash
docker compose logs | grep -i error
docker compose logs mineru-worker-cpu | grep -i error
```

## 调试技巧

### 进入容器调试

```bash
# 进入 API 容器
docker compose exec mineru-api bash

# 进入 Worker 容器
docker compose exec mineru-worker-cpu bash
```

### 检查环境变量

```bash
# 检查 API 环境变量
docker compose exec mineru-api env

# 检查 Worker 环境变量
docker compose exec mineru-worker-cpu env
```

### 测试 Redis 连接

```bash
docker compose exec mineru-api python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### 测试存储连接

```bash
# 测试本地存储
docker compose exec mineru-api ls -la /tmp/mineru_temp

# 测试 S3 存储（在容器内）
docker compose exec mineru-api python -c "from shared.storage import get_storage; s = get_storage(); print(s.storage_type)"
```

## 获取帮助

如果以上方案都无法解决问题：

1. 查看完整日志: `docker compose logs > logs.txt`
2. 检查系统资源: `docker stats`
3. 查看 GitHub Issues: [Issues](https://github.com/wzdavid/mineru-api/issues)
4. 提交新 Issue，包含：
   - 错误信息
   - 日志输出
   - 配置信息（隐藏敏感信息）
   - 复现步骤

## 更多信息

- [部署指南](DEPLOYMENT.md)
- [配置参考](CONFIGURATION.md)
- [存储配置](S3_STORAGE.md)
