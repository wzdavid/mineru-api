# Docker 配置

本目录包含所有 Docker 相关配置文件。

## 语言

- [English](README.md)
- [中文](README.zh.md) (当前)

## 文件说明

- `Dockerfile.api` - API 服务镜像
- `Dockerfile.worker` - GPU Worker 镜像（基于 Dockerfile.base）
- `Dockerfile.worker.cpu` - CPU Worker 镜像
- `Dockerfile.cleanup` - 清理服务镜像
- `Dockerfile.base` - 基础镜像（MinerU vLLM）
- `docker-compose.yml` - Docker Compose 配置

## 使用方法

### 快速开始

1. **在 `docker/.env` 中配置**：
   ```bash
   cd docker
   cp .env.example .env
   # 编辑 .env 并设置 COMPOSE_PROFILES（例如：mineru-cpu 或 mineru-gpu）
   ```

2. **启动所有服务**：
   ```bash
   cd docker && docker compose up -d
   ```

   Docker Compose 会自动从 `docker/.env` 读取 `COMPOSE_PROFILES` 并启动相应的服务。

### Worker 选择

在 `docker/.env` 中配置 Worker 类型：

```bash
# 使用 CPU Worker（推荐用于开发环境）
COMPOSE_PROFILES=mineru-cpu

# 使用 GPU Worker（需要 NVIDIA GPU）
COMPOSE_PROFILES=mineru-gpu

# 组合多个 profiles（例如：包含内部 Redis）
COMPOSE_PROFILES=redis,mineru-cpu
```

### 手动选择 Profile

您也可以手动指定 profiles：

```bash
# 启动 CPU Worker 和内部 Redis
cd docker && docker compose --profile redis --profile mineru-cpu up -d

# 启动 GPU Worker（不包含内部 Redis，使用外部 Redis）
cd docker && docker compose --profile mineru-gpu up -d

# 仅启动 API（不启动 Worker）
cd docker && docker compose up -d
```

### 查看日志和停止服务

```bash
# 查看日志
cd docker && docker compose logs -f

# 停止服务
cd docker && docker compose down
```

### Redis 配置

#### 选项 1：使用内部 Redis（推荐用于开发环境）

**方法 1：在 `docker/.env` 中使用 COMPOSE_PROFILES**：
```bash
# 在 docker/.env 中
COMPOSE_PROFILES=redis,mineru-cpu
```

然后启动服务：
```bash
cd docker && docker compose up -d
```

**方法 2：使用命令行**：
```bash
cd docker && docker compose --profile redis up -d
```

在项目根目录的 `.env` 文件中配置：
```bash
REDIS_URL=redis://redis:6379/0
```

#### 选项 2：使用主机上的外部 Redis

如果您的主机或其他容器上已有 Redis 运行：

1. **在项目根目录的 `.env` 文件中配置**：
   ```bash
   # Docker Desktop (Mac/Windows)
   REDIS_URL=redis://host.docker.internal:6379/0
   
   # Linux 系统，使用主机网络或实际 IP
   REDIS_URL=redis://172.17.0.1:6379/0
   # 或者如果 Redis 在另一台机器上
   REDIS_URL=redis://192.168.1.100:6379/0
   ```

2. **在 `docker/.env` 中配置（不包含 redis profile）**：
   ```bash
   # 只包含 worker profile，不包含 redis
   COMPOSE_PROFILES=mineru-cpu
   ```

3. **启动服务**：
   ```bash
   cd docker && docker compose up -d
   ```

#### 选项 3：解决端口冲突

如果端口 6379 已被其他 Redis 实例使用：

1. **在 `docker/.env` 中修改 Redis 端口**：
   ```bash
   REDIS_PORT=6380
   ```

2. **在项目根目录的 `.env` 中更新 `REDIS_URL`**：
   ```bash
   REDIS_URL=redis://redis:6379/0  # 容器内部端口仍然是 6379
   # 或者对于不同端口的外部 Redis
   REDIS_URL=redis://host.docker.internal:6380/0
   ```

#### 带认证的 Redis

如果您的外部 Redis 需要认证：

```bash
# 仅密码
REDIS_URL=redis://:password@host.docker.internal:6379/0

# 用户名和密码
REDIS_URL=redis://username:password@host.docker.internal:6379/0
```

## 构建镜像

```bash
# 构建所有镜像
cd docker && docker compose build

# 构建特定服务
cd docker && docker compose build mineru-api
cd docker && docker compose build mineru-worker-cpu
```

## 环境变量

### Docker 构建配置

对于 Docker 构建配置（例如用于 pip 镜像源的 `PIP_INDEX_URL`），请在 `docker/` 目录创建 `.env` 文件：

```bash
cd docker
cp .env.example .env
# 编辑 .env 并设置 PIP_INDEX_URL 为您偏好的 pip 镜像源
```

此 `.env` 文件用于 Docker Compose 的构建参数（例如 `PIP_INDEX_URL`）。

### 应用运行时配置

对于应用运行时配置，请确保在项目根目录有 `.env` 文件（从项目根目录的 `.env.example` 复制）。

Docker Compose 会自动读取 `../.env` 文件作为运行时环境变量。

## 注意事项

- 所有 Dockerfile 的构建上下文（context）是项目根目录（`..`）
- 文件路径相对于项目根目录
- 卷挂载路径也相对于项目根目录
