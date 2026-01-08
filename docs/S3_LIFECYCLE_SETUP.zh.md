# S3 生命周期策略配置指南

## 概述

使用 S3 存储时，可以配置 S3 生命周期策略来自动清理临时文件，减少应用层清理的负担。

## 为什么需要生命周期策略？

1. **临时文件清理**：临时文件通常在 24 小时内不再需要，可以通过生命周期策略自动删除
2. **减少应用负载**：自动清理减少应用层清理脚本的执行频率
3. **降低成本**：及时删除不需要的文件，减少存储成本

## 配置方法

### MinIO 配置

#### 方法 1：使用 MinIO 控制台

1. 访问 MinIO 控制台（通常是 `http://localhost:9001`）
2. 选择 bucket（如 `mineru-temp`）
3. 进入 "Lifecycle" 设置
4. 添加规则：
   - **规则名称**：`DeleteTempFiles`
   - **前缀**：空（匹配所有文件）
   - **过期时间**：1 天（24小时）

#### 方法 2：使用 boto3 脚本

创建脚本 `setup_mineru_s3_lifecycle.py`：

```python
#!/usr/bin/env python3
"""配置 MinerU S3 存储的生命周期策略"""
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

def setup_lifecycle_policy():
    """配置 MinerU S3 bucket 的生命周期策略"""
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('MINERU_S3_ENDPOINT', 'http://localhost:9000'),
        # NOTE: Replace 'minioadmin' with your actual credentials in production
        aws_access_key_id=os.getenv('MINERU_S3_ACCESS_KEY', 'minioadmin'),
        aws_secret_access_key=os.getenv('MINERU_S3_SECRET_KEY', 'minioadmin'),
        region_name=os.getenv('MINERU_S3_REGION', 'us-east-1')
    )
    
    # 临时文件 bucket：24 小时后自动删除
    temp_bucket = os.getenv('MINERU_S3_BUCKET_TEMP', 'mineru-temp')
    temp_lifecycle = {
        'Rules': [{
            'ID': 'DeleteTempFiles',
            'Status': 'Enabled',
            'Filter': {'Prefix': ''},
            'Expiration': {'Days': 1}
        }]
    }
    
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=temp_bucket,
            LifecycleConfiguration=temp_lifecycle
        )
        print(f"✅ 已为 {temp_bucket} 配置生命周期策略（24小时自动删除）")
    except ClientError as e:
        print(f"❌ 配置失败: {e}")
    
    # 输出文件 bucket：不配置自动删除，由应用层清理脚本管理
    # 因为输出文件需要根据 RESULT_EXPIRES 配置和任务完成时间来判断
    output_bucket = os.getenv('MINERU_S3_BUCKET_OUTPUT', 'mineru-output')
    print(f"ℹ️  {output_bucket} 使用应用层清理脚本管理（根据 RESULT_EXPIRES 配置）")

if __name__ == '__main__':
    setup_lifecycle_policy()
```

运行脚本：
```bash
python setup_mineru_s3_lifecycle.py
```

#### 方法 3：使用 s3fs（不推荐）

s3fs 主要用于文件系统操作，不直接支持生命周期策略配置。建议使用 boto3 或 MinIO 客户端。

### AWS S3 配置

如果使用 AWS S3，可以通过 AWS 控制台或 CLI 配置：

```bash
# 使用 AWS CLI 配置生命周期策略
aws s3api put-bucket-lifecycle-configuration \
  --bucket mineru-temp \
  --lifecycle-configuration file://lifecycle.json
```

`lifecycle.json` 内容：
```json
{
  "Rules": [
    {
      "ID": "DeleteTempFiles",
      "Status": "Enabled",
      "Filter": {},
      "Expiration": {
        "Days": 1
      }
    }
  ]
}
```

## 推荐配置

### 临时文件 Bucket (`mineru-temp`)

- **生命周期策略**：24 小时后自动删除
- **理由**：临时文件通常在任务完成后立即不再需要，24 小时足够安全

### 输出文件 Bucket (`mineru-output`)

- **不配置自动删除**：由应用层清理脚本管理
- **理由**：
  - 输出文件需要根据 `RESULT_EXPIRES` 配置清理
  - 需要根据任务完成时间判断，而不是文件创建时间
  - 需要更灵活的清理逻辑（如按任务ID、目录结构等）

## 验证配置

### 检查生命周期策略

```python
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    # NOTE: Replace with your actual credentials in production
    aws_access_key_id='minioadmin',  # Replace with your actual access key
    aws_secret_access_key='minioadmin'  # Replace with your actual secret key
)

# 获取生命周期策略
response = s3_client.get_bucket_lifecycle_configuration(Bucket='mineru-temp')
print(response)
```

### 测试自动删除

1. 上传一个测试文件到 `mineru-temp` bucket
2. 等待 24 小时（或修改策略为更短时间进行测试）
3. 检查文件是否被自动删除

## 注意事项

1. **时间计算**：S3 生命周期策略基于对象的最后修改时间，不是创建时间
2. **时区**：确保 S3 服务和应用使用相同的时区
3. **不可逆**：文件被生命周期策略删除后无法恢复
4. **成本**：及时清理可以减少存储成本，但要注意不要误删重要文件

## 与清理脚本的配合

- **临时文件**：S3 生命周期策略自动清理（24小时）
- **输出文件**：cleanup 脚本清理（根据 `RESULT_EXPIRES` 配置）

这样可以：
- 减少应用层清理脚本的执行频率
- 降低应用负载
- 保持清理逻辑的灵活性

