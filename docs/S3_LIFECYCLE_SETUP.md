# S3 Lifecycle Policy Configuration Guide

## Overview

When using S3 storage, you can configure S3 lifecycle policies to automatically clean temporary files, reducing the burden of application-layer cleanup.

## Why Do We Need Lifecycle Policies?

1. **Temporary File Cleanup**: Temporary files are usually no longer needed within 24 hours and can be automatically deleted via lifecycle policies
2. **Reduce Application Load**: Automatic cleanup reduces the execution frequency of application-layer cleanup scripts
3. **Reduce Costs**: Timely deletion of unnecessary files reduces storage costs

## Configuration Methods

### MinIO Configuration

#### Method 1: Using MinIO Console

1. Access MinIO console (usually `http://localhost:9001`)
2. Select bucket (e.g., `mineru-temp`)
3. Go to "Lifecycle" settings
4. Add rule:
   - **Rule Name**: `DeleteTempFiles`
   - **Prefix**: Empty (matches all files)
   - **Expiration Time**: 1 day (24 hours)

#### Method 2: Using boto3 Script

Create script `setup_mineru_s3_lifecycle.py`:

```python
#!/usr/bin/env python3
"""Configure MinerU S3 storage lifecycle policy"""
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

def setup_lifecycle_policy():
    """Configure MinerU S3 bucket lifecycle policy"""
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('MINERU_S3_ENDPOINT', 'http://localhost:9000'),
        # NOTE: Replace 'minioadmin' with your actual credentials in production
        aws_access_key_id=os.getenv('MINERU_S3_ACCESS_KEY', 'minioadmin'),
        aws_secret_access_key=os.getenv('MINERU_S3_SECRET_KEY', 'minioadmin'),
        region_name=os.getenv('MINERU_S3_REGION', 'us-east-1')
    )
    
    # Temporary files bucket: Auto-delete after 24 hours
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
        print(f"✅ Lifecycle policy configured for {temp_bucket} (auto-delete after 24 hours)")
    except ClientError as e:
        print(f"❌ Configuration failed: {e}")
    
    # Output files bucket: Do not configure auto-deletion, managed by application-layer cleanup script
    # Because output files need to be cleaned based on RESULT_EXPIRES configuration and task completion time
    output_bucket = os.getenv('MINERU_S3_BUCKET_OUTPUT', 'mineru-output')
    print(f"ℹ️  {output_bucket} managed by application-layer cleanup script (based on RESULT_EXPIRES configuration)")

if __name__ == '__main__':
    setup_lifecycle_policy()
```

Run script:
```bash
python setup_mineru_s3_lifecycle.py
```

#### Method 3: Using s3fs (Not Recommended)

s3fs is mainly for filesystem operations and does not directly support lifecycle policy configuration. Recommend using boto3 or MinIO client.

### AWS S3 Configuration

If using AWS S3, configure via AWS console or CLI:

```bash
# Use AWS CLI to configure lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket mineru-temp \
  --lifecycle-configuration file://lifecycle.json
```

`lifecycle.json` content:
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

## Recommended Configuration

### Temporary Files Bucket (`mineru-temp`)

- **Lifecycle Policy**: Auto-delete after 24 hours
- **Reason**: Temporary files are usually no longer needed immediately after task completion, 24 hours is safe enough

### Output Files Bucket (`mineru-output`)

- **Do not configure auto-deletion**: Managed by application-layer cleanup script
- **Reasons**:
  - Output files need cleanup based on `RESULT_EXPIRES` configuration
  - Need to judge based on task completion time, not file creation time
  - Need more flexible cleanup logic (such as by task ID, directory structure, etc.)

## Verify Configuration

### Check Lifecycle Policy

```python
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    # NOTE: Replace with your actual credentials in production
    aws_access_key_id='minioadmin',  # Replace with your actual access key
    aws_secret_access_key='minioadmin'  # Replace with your actual secret key
)

# Get lifecycle policy
response = s3_client.get_bucket_lifecycle_configuration(Bucket='mineru-temp')
print(response)
```

### Test Auto-Deletion

1. Upload a test file to `mineru-temp` bucket
2. Wait 24 hours (or modify policy to shorter time for testing)
3. Check if file was automatically deleted

## Notes

1. **Time Calculation**: S3 lifecycle policies are based on object's last modification time, not creation time
2. **Time Zone**: Ensure S3 service and application use the same time zone
3. **Irreversible**: Files deleted by lifecycle policy cannot be recovered
4. **Cost**: Timely cleanup can reduce storage costs, but be careful not to accidentally delete important files

## Coordination with Cleanup Script

- **Temporary Files**: S3 lifecycle policy automatic cleanup (24 hours)
- **Output Files**: Cleanup script cleanup (based on `RESULT_EXPIRES` configuration)

This approach:
- Reduces application-layer cleanup script execution frequency
- Lowers application load
- Maintains cleanup logic flexibility
