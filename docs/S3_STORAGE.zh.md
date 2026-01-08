# MinerU S3 存储支持方案

## 概述

MinerU 现在支持使用 S3 兼容存储（如 MinIO）来管理临时文件和输出文件，这使得分布式部署成为可能。API 和 Worker 可以部署在不同的机器上，无需共享文件系统。

## 架构设计

### 存储抽象层

创建了统一的存储抽象层 `shared/storage.py`，提供以下功能：

- **StorageAdapter 类**：统一的存储接口
  - `save_temp_file()`: 保存临时文件
  - `save_output_file()`: 保存输出文件
  - `read_file()`: 读取文件
  - `download_to_local()`: 下载到本地（用于需要本地文件路径的操作）
  - `upload_from_local()`: 从本地上传
  - `delete_file()`: 删除文件
  - `list_files()`: 列出文件

- **支持的存储类型**：
  - `local`: 本地文件系统（通过 Docker volume 共享）
  - `s3`: S3 兼容存储（支持 MinIO、AWS S3 等）

### 工作流程

#### 本地存储模式（默认）

```
API 容器 → 写入 /tmp/mineru_temp → Docker Volume → Worker 容器读取
Worker 容器 → 写入 /tmp/mineru_output → Docker Volume → API 容器读取
```

#### S3 存储模式

```
API 容器 → 上传到 S3 (mineru-temp bucket) → Worker 容器下载
Worker 容器 → 处理 → 上传到 S3 (mineru-output bucket) → API 容器读取
```

## 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# 存储类型：local 或 s3
MINERU_STORAGE_TYPE=local

# 本地存储配置（仅在 MINERU_STORAGE_TYPE=local 时使用）
TEMP_DIR=/tmp/mineru_temp
OUTPUT_DIR=/tmp/mineru_output

# S3 存储配置（仅在 MINERU_STORAGE_TYPE=s3 时使用）
MINERU_S3_ENDPOINT=http://minio:9000
MINERU_S3_ACCESS_KEY=minioadmin
MINERU_S3_SECRET_KEY=minioadmin
MINERU_S3_BUCKET_TEMP=mineru-temp
MINERU_S3_BUCKET_OUTPUT=mineru-output
MINERU_S3_SECURE=false
MINERU_S3_REGION=
```

### 使用本地存储（单机部署）

```bash
# .env 文件
MINERU_STORAGE_TYPE=local
TEMP_DIR=/tmp/mineru_temp
OUTPUT_DIR=/tmp/mineru_output
```

### 使用 S3 存储（分布式部署）

```bash
# .env 文件
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio:9000
MINERU_S3_ACCESS_KEY=minioadmin
MINERU_S3_SECRET_KEY=minioadmin
MINERU_S3_BUCKET_TEMP=mineru-temp
MINERU_S3_BUCKET_OUTPUT=mineru-output
MINERU_S3_SECURE=false
```

## 部署示例

### 单机部署（本地存储）

```bash
# 所有服务在同一台机器上
docker compose up -d mineru-api
docker compose --profile mineru-cpu up -d
```

### 分布式部署（S3 存储）

**机器 A（API 服务）**：
```bash
# .env 配置
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio.example.com:9000
# ... 其他 S3 配置

# 启动 API
docker compose up -d mineru-api
```

**机器 B、C、D（Worker 服务）**：
```bash
# .env 配置（与机器 A 相同）
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio.example.com:9000
# ... 其他 S3 配置

# 启动 Worker
docker compose --profile mineru-cpu up -d
```

## 代码变更

### 新增文件

- `shared/storage.py`: 存储抽象层实现

### 修改文件

- `api/app.py`: 使用存储适配器处理文件上传
- `worker/tasks.py`: 使用存储适配器处理文件读写
- `cleanup/cleanup_outputs.py`: 支持 S3 存储的清理功能
- `.env.example`: 添加 S3 存储配置示例
- `docker-compose-mineru.yml`: 添加 S3 模式说明注释
- `README.md`: 更新部署文档

### 依赖更新

- `api/requirements.txt`: 添加 `s3fs>=2024.3.0`
- `worker/requirements.txt`: 添加 `s3fs>=2024.3.0`

## 优势

1. **分布式部署**：API 和 Worker 可以部署在不同机器上
2. **向后兼容**：默认使用本地存储，不影响现有部署
3. **统一接口**：通过存储抽象层，代码无需关心底层存储实现
4. **易于扩展**：可以轻松添加其他存储后端（如 SeaweedFS）

## 清理策略

### 使用 S3 存储时的清理方案

使用 S3 存储时，有两种清理方式可以结合使用：

#### 1. S3 生命周期策略（推荐用于临时文件）

S3 服务端可以配置生命周期策略，自动删除过期文件。这种方式更高效，适合简单的过期删除。

**配置示例（MinIO）**：
```bash
# 使用 boto3 或 MinIO 客户端配置生命周期策略
# 临时文件 bucket：24 小时后自动删除
# 输出文件 bucket：根据业务需求配置（建议使用应用层清理）
```

**优势**：
- 自动执行，无需应用层代码
- 减少网络请求
- 降低应用负载

**限制**：
- 只能按时间删除，无法按任务ID、业务逻辑等条件删除
- 配置相对固定，不够灵活

#### 2. 应用层清理脚本（推荐用于输出文件）

使用 `cleanup_outputs.py` 脚本进行清理，支持更复杂的清理逻辑。

**使用场景**：
- 输出文件需要根据 `RESULT_EXPIRES` 配置和任务完成时间清理
- 需要按任务ID、目录结构等条件清理
- 需要预览将要删除的文件

**推荐配置**：
- **临时文件**：使用 S3 生命周期策略（24小时自动删除）
- **输出文件**：使用 cleanup 脚本（根据 `RESULT_EXPIRES` 配置清理）

### 清理脚本使用

```bash
# 预览模式（查看将要删除的文件）
python cleanup/cleanup_outputs.py --dry-run

# 实际清理
python cleanup/cleanup_outputs.py

# 只清理输出目录（临时文件由S3生命周期策略处理）
python cleanup/cleanup_outputs.py --output-only
```

## 注意事项

1. **S3 Bucket 创建**：首次使用 S3 存储时，系统会自动创建所需的 bucket
2. **网络连接**：确保所有容器都能访问 S3 服务
3. **性能考虑**：S3 存储会有网络延迟，但支持分布式部署的优势明显
4. **清理策略**：
   - **临时文件**：建议配置 S3 生命周期策略（24小时自动删除）
   - **输出文件**：使用 cleanup 脚本，根据 `RESULT_EXPIRES` 配置清理
5. **清理脚本**：清理脚本已支持 S3 存储，会自动检测存储类型

## 故障排除

### S3 连接失败

检查：
- S3 服务是否运行
- 网络连接是否正常
- 访问密钥是否正确
- Bucket 是否存在（会自动创建）

### 文件读取失败

检查：
- 文件路径是否正确
- S3 权限配置是否正确
- 网络连接是否稳定

## 未来改进

1. 支持更多存储后端（SeaweedFS、Azure Blob Storage 等）
2. 添加存储性能监控
3. 支持存储加密
4. 优化大文件传输性能

