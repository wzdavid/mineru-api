# MinerU S3 Storage Support

## Overview

MinerU now supports using S3-compatible storage (such as MinIO) to manage temporary and output files, enabling distributed deployment. API and Worker can be deployed on different machines without requiring a shared filesystem.

## Architecture Design

### Storage Abstraction Layer

A unified storage abstraction layer `shared/storage.py` has been created, providing the following features:

- **StorageAdapter class**: Unified storage interface
  - `save_temp_file()`: Save temporary files
  - `save_output_file()`: Save output files
  - `read_file()`: Read files
  - `download_to_local()`: Download to local (for operations requiring local file paths)
  - `upload_from_local()`: Upload from local
  - `delete_file()`: Delete files
  - `list_files()`: List files

- **Supported storage types**:
  - `local`: Local filesystem (shared via Docker volume)
  - `s3`: S3-compatible storage (supports MinIO, AWS S3, etc.)

### Workflow

#### Local Storage Mode (Default)

```
API Container → Write to /tmp/mineru_temp → Docker Volume → Worker Container reads
Worker Container → Write to /tmp/mineru_output → Docker Volume → API Container reads
```

#### S3 Storage Mode

```
API Container → Upload to S3 (mineru-temp bucket) → Worker Container downloads
Worker Container → Process → Upload to S3 (mineru-output bucket) → API Container reads
```

## Configuration

### Environment Variables

Configure in `.env` file:

```bash
# Storage type: local or s3
MINERU_STORAGE_TYPE=local

# Local storage configuration (only used when MINERU_STORAGE_TYPE=local)
TEMP_DIR=/tmp/mineru_temp
OUTPUT_DIR=/tmp/mineru_output

# S3 storage configuration (only used when MINERU_STORAGE_TYPE=s3)
MINERU_S3_ENDPOINT=http://minio:9000
MINERU_S3_ACCESS_KEY=minioadmin
MINERU_S3_SECRET_KEY=minioadmin
MINERU_S3_BUCKET_TEMP=mineru-temp
MINERU_S3_BUCKET_OUTPUT=mineru-output
MINERU_S3_SECURE=false
MINERU_S3_REGION=
```

### Using Local Storage (Single Machine Deployment)

```bash
# .env file
MINERU_STORAGE_TYPE=local
TEMP_DIR=/tmp/mineru_temp
OUTPUT_DIR=/tmp/mineru_output
```

### Using S3 Storage (Distributed Deployment)

```bash
# .env file
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio:9000
MINERU_S3_ACCESS_KEY=minioadmin
MINERU_S3_SECRET_KEY=minioadmin
MINERU_S3_BUCKET_TEMP=mineru-temp
MINERU_S3_BUCKET_OUTPUT=mineru-output
MINERU_S3_SECURE=false
```

## Deployment Examples

### Single Machine Deployment (Local Storage)

```bash
# All services on the same machine
cd docker && docker compose up -d mineru-api
cd docker && docker compose --profile mineru-cpu up -d
```

### Distributed Deployment (S3 Storage)

**Machine A (API Service)**:
```bash
# .env configuration
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio.example.com:9000
# ... other S3 configuration

# Start API
cd docker && docker compose up -d mineru-api
```

**Machine B, C, D (Worker Services)**:
```bash
# .env configuration (same as Machine A)
MINERU_STORAGE_TYPE=s3
MINERU_S3_ENDPOINT=http://minio.example.com:9000
# ... other S3 configuration

# Start Worker
cd docker && docker compose --profile mineru-cpu up -d
```

## Code Changes

### New Files

- `shared/storage.py`: Storage abstraction layer implementation

### Modified Files

- `api/app.py`: Use storage adapter for file uploads
- `worker/tasks.py`: Use storage adapter for file read/write
- `cleanup/cleanup_outputs.py`: Support S3 storage cleanup functionality
- `.env.example`: Add S3 storage configuration examples
- `docker/docker-compose.yml`: Add S3 mode description comments
- `README.md`: Update deployment documentation

### Dependency Updates

- `api/requirements.txt`: Add `s3fs>=2024.3.0`
- `worker/requirements.txt`: Add `s3fs>=2024.3.0`

## Advantages

1. **Distributed Deployment**: API and Worker can be deployed on different machines
2. **Backward Compatible**: Default to local storage, does not affect existing deployments
3. **Unified Interface**: Through storage abstraction layer, code doesn't need to care about underlying storage implementation
4. **Easy to Extend**: Can easily add other storage backends (such as SeaweedFS)

## Cleanup Strategy

### Cleanup Solutions When Using S3 Storage

When using S3 storage, two cleanup methods can be combined:

#### 1. S3 Lifecycle Policy (Recommended for Temporary Files)

S3 service can configure lifecycle policies to automatically delete expired files. This method is more efficient and suitable for simple expiration deletion.

**Configuration Example (MinIO)**:
```bash
# Use boto3 or MinIO client to configure lifecycle policy
# Temporary files bucket: Auto-delete after 24 hours
# Output files bucket: Configure based on business needs (recommend using application-layer cleanup)
```

**Advantages**:
- Automatic execution, no application-layer code needed
- Reduces network requests
- Lowers application load

**Limitations**:
- Can only delete by time, cannot delete by task ID, business logic, etc.
- Configuration is relatively fixed, not flexible enough

#### 2. Application-Layer Cleanup Script (Recommended for Output Files)

Use `cleanup_outputs.py` script for cleanup, supporting more complex cleanup logic.

**Use Cases**:
- Output files need cleanup based on `RESULT_EXPIRES` configuration and task completion time
- Need to cleanup by task ID, directory structure, etc.
- Need to preview files to be deleted

**Recommended Configuration**:
- **Temporary Files**: Use S3 lifecycle policy (auto-delete after 24 hours)
- **Output Files**: Use cleanup script (cleanup based on `RESULT_EXPIRES` configuration)

### Cleanup Script Usage

```bash
# Preview mode (view files to be deleted)
python cleanup/cleanup_outputs.py --dry-run

# Actual cleanup
python cleanup/cleanup_outputs.py

# Only cleanup output directory (temporary files handled by S3 lifecycle policy)
python cleanup/cleanup_outputs.py --output-only
```

## Notes

1. **S3 Bucket Creation**: System will automatically create required buckets on first use of S3 storage
2. **Network Connection**: Ensure all containers can access S3 service
3. **Performance Considerations**: S3 storage has network latency, but the advantage of supporting distributed deployment is significant
4. **Cleanup Strategy**:
   - **Temporary Files**: Recommend configuring S3 lifecycle policy (auto-delete after 24 hours)
   - **Output Files**: Use cleanup script, cleanup based on `RESULT_EXPIRES` configuration
5. **Cleanup Script**: Cleanup script already supports S3 storage and will automatically detect storage type

## Troubleshooting

### S3 Connection Failed

Check:
- Is S3 service running
- Is network connection normal
- Are access keys correct
- Do buckets exist (will be created automatically)

### File Read Failed

Check:
- Is file path correct
- Is S3 permission configuration correct
- Is network connection stable

## Future Improvements

1. Support more storage backends (SeaweedFS, Azure Blob Storage, etc.)
2. Add storage performance monitoring
3. Support storage encryption
4. Optimize large file transfer performance
