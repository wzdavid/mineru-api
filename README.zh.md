# MinerU Parsing Service

[![CI](https://github.com/wzdavid/mineru-api/workflows/CI/badge.svg)](https://github.com/wzdavid/mineru-api/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

企业级文档解析服务，基于 Celery 实现异步队列处理，采用完全解耦的 API/Worker 架构。

## 功能特性

- 🚀 **异步处理**: 基于 Celery 的分布式任务队列
- 📄 **多格式支持**: PDF、Office、图片等多种文档格式
- 🔄 **高可用性**: 支持任务重试和故障恢复
- 📊 **实时监控**: 任务状态跟踪和队列统计
- 🎯 **优先级队列**: 支持任务优先级调度
- 🔧 **易于扩展**: 模块化设计，易于添加新的解析引擎

## 快速开始

### 前置准备

- Docker 和 Docker Compose
- （可选）NVIDIA GPU（用于 GPU Worker）

### 启动服务

1. **复制环境配置文件**:
   ```bash
   cp .env.example .env
   ```

2. **启动 Redis 和 API**:
   ```bash
   cd docker && docker compose up -d redis mineru-api
   ```

3. **启动 Worker**（选择 CPU 或 GPU）:
   ```bash
   # CPU Worker（推荐开发环境）
   cd docker && docker compose --profile mineru-cpu up -d

   # GPU Worker（需要 NVIDIA GPU）
   cd docker && docker compose --profile mineru-gpu up -d
   ```

4. **验证服务**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

完成！API 现在运行在 `http://localhost:8000`。

## API 使用

MinerU-API 提供了两种 API 接口，以适应不同的使用场景：

### 1. MinerU 官方 API（同步）

`/file_parse` 端点兼容 MinerU 官方 API 格式。它将任务提交到 worker 并等待完成，直接在响应中返回结果。

**参考**: [MinerU 官方 API](https://github.com/opendatalab/MinerU/blob/master/mineru/cli/fast_api.py)

```bash
curl -X POST "http://localhost:8000/file_parse" \
  -F "files=@document.pdf" \
  -F "backend=pipeline" \
  -F "lang_list=ch" \
  -F "parse_method=auto" \
  -F "return_md=true"
```

**适用场景**: 简单集成、需要立即获取结果、兼容现有 MinerU 客户端。

### 2. 异步队列 API（异步）

`/api/v1/tasks/submit` 和 `/api/v1/tasks/{task_id}` 端点提供基于异步队列的 API，兼容 mineru-tianshu 项目格式。

**参考**: [mineru-tianshu API](https://github.com/magicyuan876/mineru-tianshu/blob/main/backend/README.md)

**提交任务**:
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/submit" \
  -F "file=@document.pdf" \
  -F "backend=pipeline" \
  -F "lang=ch"
```

**查询任务状态**:
```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

**适用场景**: 生产环境部署、批量处理、长时间运行的任务、更好的可扩展性。

### 查看 API 文档

访问 `http://localhost:8000/docs` 查看包含完整参数详情的交互式 API 文档。

## 基本配置

### 环境变量

最重要的配置选项（查看 `.env.example` 获取所有选项）：

```bash
# Redis 配置
REDIS_URL=redis://redis:6379/0

# 存储类型：local 或 s3
MINERU_STORAGE_TYPE=local

# S3 存储配置（分布式部署）
MINERU_S3_ENDPOINT=http://minio:9000
MINERU_S3_ACCESS_KEY=minioadmin
MINERU_S3_SECRET_KEY=minioadmin

# CORS 配置（生产环境）
CORS_ALLOWED_ORIGINS=http://localhost:3000
ENVIRONMENT=production

# 文件上传限制
MAX_FILE_SIZE=104857600  # 100MB
```

## 文档

- [📖 完整文档](docs/README.zh.md) - 完整指南和配置说明 ([English](docs/README.md))
- [🚀 部署指南](docs/DEPLOYMENT.zh.md) - 生产环境部署 ([English](docs/DEPLOYMENT.md))
- [⚙️ 配置参考](docs/CONFIGURATION.zh.md) - 所有配置选项 ([English](docs/CONFIGURATION.md))
- [💡 API 示例](docs/API_EXAMPLES.zh.md) - 多语言代码示例 ([English](docs/API_EXAMPLES.md))
- [🔧 故障排除](docs/TROUBLESHOOTING.zh.md) - 常见问题和解决方案 ([English](docs/TROUBLESHOOTING.md))
- [🧹 存储与清理](docs/S3_STORAGE.zh.md) - 存储配置和清理 ([English](docs/S3_STORAGE.md))

## 架构

- **API 服务**: 处理任务提交和状态查询 (`api/app.py`)
- **Worker 服务**: 使用 MinerU/MarkItDown 处理文档 (`worker/tasks.py`)
- **Redis**: 消息队列和结果存储
- **共享配置**: 统一配置在 `shared/celeryconfig.py`

## 开发

```bash
# 安装依赖
pip install -r api/requirements.txt
pip install -r worker/requirements.txt
pip install -r cleanup/requirements.txt
```

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

## 致谢

本项目基于以下优秀的开源项目构建：

- **[MinerU](https://github.com/opendatalab/MinerU)** - 提供核心文档解析引擎
- **[mineru-tianshu](https://github.com/magicyuan876/mineru-tianshu)** - API 架构的参考和灵感来源

我们感谢这些项目的开发者和贡献者的宝贵工作。

## 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件了解详情。

### 第三方许可证

本项目使用以下开源库：

- **MinerU** - 使用 [AGPL-3.0](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md) 许可证
- **MarkItDown** - 使用 [MIT](https://github.com/microsoft/markitdown) 许可证

MinerU 作为外部库使用，其源代码未包含在本仓库中。
