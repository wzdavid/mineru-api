"""MinerU Celery Tasks
MinerU document processing task definitions

Provides asynchronous MinerU document parsing tasks based on Celery
"""
import os
import sys
import json
import gc
from pathlib import Path
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import traceback
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Add path to import components
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery, states
from celery.utils.log import get_task_logger
from shared import celeryconfig
from shared.storage import get_storage

if os.getenv('MINERU_DEVICE_MODE') == None or os.getenv('MINERU_DEVICE_MODE') == '' or os.getenv('MINERU_DEVICE_MODE') == 'auto':
    # Delete empty or 'auto' value to let MinerU automatically detect device type
    del os.environ['MINERU_DEVICE_MODE']

import threading
# PyPDFium2 only supports single-threaded usage
pypdfium2_lock = threading.Lock()

# Initialize MinerU models config if missing
def _init_mineru_models_config():
    """Initialize MinerU models config file if it doesn't exist"""
    import json
    from pathlib import Path as P
    config_path = P.home() / '.mineru' / 'models_config.json'
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {'pipeline': {}, 'vlm': {}}
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"✅ Initialized MinerU models config at {config_path}")

_init_mineru_models_config()

# Celery application
celery_app = Celery('mineru_worker')
celery_app.config_from_object(celeryconfig)

# MinerU related imports
try:
    from mineru.cli.common import do_parse, read_fn
    from mineru.utils.config_reader import get_device
    from mineru.utils.model_utils import get_vram, clean_memory
    MINERU_AVAILABLE = True
except ImportError:
    MINERU_AVAILABLE = False

# MarkItDown imports
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

# MinIO imports
try:
    from minio import Minio
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

logger = get_task_logger(__name__)

# Configuration constants
OUTPUT_DIR = Path(celeryconfig.OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Supported file formats
PDF_IMAGE_FORMATS = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}

# MIME type mapping
MIME_TYPE_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.webp': 'image/webp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff'
}

# MinIO configuration
MINIO_CONFIG = {
    'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    'secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
    'bucket_name': os.getenv('MINIO_BUCKET', 'documents')
}


def get_minio_client():
    """Get MinIO client"""
    if not MINIO_AVAILABLE or not all(MINIO_CONFIG.values()):
        return None
    
    return Minio(
        MINIO_CONFIG['endpoint'],
        access_key=MINIO_CONFIG['access_key'],
        secret_key=MINIO_CONFIG['secret_key'],
        secure=MINIO_CONFIG['secure']
    )


def get_file_type(file_path: str) -> str:
    """
    Determine file type
    
    Returns:
        'pdf_image': PDF or image format, use MinerU parsing
        'markitdown': All other formats, use markitdown parsing
    """
    suffix = Path(file_path).suffix.lower()
    
    if suffix in PDF_IMAGE_FORMATS:
        return 'pdf_image'
    else:
        return 'markitdown'


def process_markdown_images_base64(md_content: str, image_dir: Path) -> str:
    """Convert images in Markdown to base64 format"""
    logger.info(f"🔄 Converting images to base64: image_dir={image_dir}")
    
    if not image_dir.exists():
        logger.warning(f"Image directory does not exist for base64 conversion: {image_dir}")
        return md_content
    
    import re
    import base64
    import mimetypes
    
    # Find all image links
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(image_pattern, md_content)
    
    if not matches:
        return md_content
    
    # MIME type mapping uses global constant
    mime_map = MIME_TYPE_MAP
    
    # Replace image links with base64
    for alt_text, image_path in matches:
        # Build full image path
        # If image_path starts with images/, remove this prefix
        if image_path.startswith('images/'):
            image_filename = image_path[7:]  # Remove 'images/' prefix
        else:
            image_filename = image_path
        
        full_image_path = image_dir / image_filename
        
        if full_image_path.exists():
            try:
                # Read image file
                with open(full_image_path, 'rb') as img_file:
                    img_data = img_file.read()
                
                # Get MIME type
                mime_type, _ = mimetypes.guess_type(str(full_image_path))
                if not mime_type or not mime_type.startswith('image/'):
                    # Set default MIME type based on file extension
                    ext = full_image_path.suffix.lower()
                    mime_type = mime_map.get(ext, 'image/png')
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Create data URL
                data_url = f"data:{mime_type};base64,{img_base64}"
                
                # Replace link in Markdown
                old_link = f"![{alt_text}]({image_path})"
                new_link = f"![{alt_text}]({data_url})"
                md_content = md_content.replace(old_link, new_link)
                
                logger.info(f"Converted image to base64: {image_path} ({len(img_data)} bytes)")
                
            except Exception as e:
                logger.error(f"Failed to convert image to base64 {image_path}: {e}")
    
    return md_content


def process_markdown_images(md_content: str, image_dir: Path, upload_images: bool = False) -> str:
    """Process image links in Markdown"""
    logger.info(f"🖼️ Processing images: upload_images={upload_images}, image_dir={image_dir}")
    
    if not image_dir.exists():
        logger.warning(f"Image directory does not exist: {image_dir}")
        return md_content
    
    if upload_images:
        # Original logic for uploading to MinIO
        import re
        
        # Find all image links
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(image_pattern, md_content)
        
        if not matches:
            return md_content
        
        minio_client = get_minio_client()
        if not minio_client:
            logger.warning("MinIO not configured, skipping image upload")
            return md_content
        
        # Replace image links
        for alt_text, image_path in matches:
            # Build full image path
            full_image_path = image_dir / image_path
            
            if full_image_path.exists():
                try:
                    # Generate unique object name
                    object_name = f"mineru/{uuid.uuid4()}/{full_image_path.name}"
                    
                    # Upload to MinIO
                    minio_client.fput_object(
                        MINIO_CONFIG['bucket_name'],
                        object_name,
                        str(full_image_path)
                    )
                    
                    # Generate access URL
                    image_url = f"https://{MINIO_CONFIG['endpoint']}/{MINIO_CONFIG['bucket_name']}/{object_name}"
                    
                    # Replace link in Markdown
                    old_link = f"![{alt_text}]({image_path})"
                    new_link = f"![{alt_text}]({image_url})"
                    md_content = md_content.replace(old_link, new_link)
                    
                    logger.info(f"Uploaded image: {image_path} -> {image_url}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload image {image_path}: {e}")
    else:
        # Default: convert to base64 format
        md_content = process_markdown_images_base64(md_content, image_dir)
    
    return md_content


@celery_app.task(
    name='mineru.parse_document',
    bind=True,
    max_retries=0,  # Disable automatic retry
    soft_time_limit=6000,     # 100 minutes
    time_limit=7200,          # 2 hours
    track_started=True
)
def parse_document_task(
    self,
    file_path: str,
    file_name: str,
    backend: str = 'pipeline',
    options: Optional[Dict[str, Any]] = None,
    upload_images: bool = False,
) -> Dict[str, Any]:
    """
    MinerU document parsing task
    
    Args:
        file_path: File path
        file_name: File name
        backend: Parsing backend ('pipeline' or 'markitdown')
        options: Parsing options
        upload_images: Whether to upload images to MinIO
        
    Returns:
        Parsing result dictionary
    """
    if options is None:
        options = {}
    
    # Explicitly output only content_list JSON
    options.update({
        'f_dump_content_list': True
    })
    options.setdefault('formula_enable', os.getenv('MINERU_FORMULA_ENABLE', 'true').lower() == 'true')
    options.setdefault('table_enable', os.getenv('MINERU_TABLE_ENABLE', 'true').lower() == 'true')
    options.setdefault('method', os.getenv('MINERU_PARSE_METHOD', 'auto'))
    options.setdefault('lang', os.getenv('MINERU_LANG', 'ch'))
    
    task_id = self.request.id
    logger.info(f"Starting MinerU document parsing task: {file_name}")
    
    # Update task status to processing
    self.update_state(
        state=states.STARTED,
        meta={
            'status': 'processing',
            'file_name': file_name,
            'backend': backend,
            'started_at': datetime.now().isoformat()
        }
    )
    
    try:
        storage = get_storage()
        
        # Download input file to local (if S3 storage, need local file path for MinerU)
        local_input_file = storage.download_to_local(file_path)
        local_input_path = Path(local_input_file)
        
        try:
            # Prepare output directory (local temporary directory, upload to storage after processing)
            import tempfile
            with tempfile.TemporaryDirectory() as temp_output_dir:
                output_path = Path(temp_output_dir) / task_id
                output_path.mkdir(parents=True, exist_ok=True)
                
                # Determine file type and select parsing method
                file_type = get_file_type(str(local_input_path))
                
                if file_type == 'pdf_image':
                    # Use MinerU to parse PDF and images
                    logger.info(f"📄 Using MinerU parser for {file_name}")
                    result = _parse_with_mineru(
                        file_path=local_input_path,
                        file_name=file_name,
                        task_id=task_id,
                        backend=backend,
                        options=options,
                        output_path=output_path
                    )
                    parse_method = 'MinerU'
                else:
                    # Use MarkItDown to parse other formats
                    logger.info(f"📊 Using MarkItDown parser for {file_name}")
                    result = _parse_with_markitdown(
                        file_path=local_input_path,
                        file_name=file_name,
                        output_path=output_path
                    )
                    parse_method = 'MarkItDown'
                
                # Read parsing results
                md_files = list(output_path.rglob('*.md'))
                if not md_files:
                    raise Exception("No markdown files generated")
                
                md_file = md_files[0]
                with open(md_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Process images (always process, default to base64 conversion)
                image_dir = md_file.parent / 'images'
                if image_dir.exists():
                    embed_images = os.getenv('MINERU_EMBED_IMAGES_IN_MD', 'true').lower() == 'true'
                    if embed_images or upload_images:
                        logger.info(f"🖼️ Processing images for task {task_id}")
                        md_content = process_markdown_images(md_content, image_dir, upload_images)
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(md_content)
                        logger.info(f"✅ Updated markdown file with processed images: {md_file}")
                
                # Upload all output files to storage
                output_key_prefix = f"{task_id}/"
                for file_path_obj in output_path.rglob('*'):
                    if file_path_obj.is_file():
                        relative_path = file_path_obj.relative_to(output_path)
                        storage_key = f"{output_key_prefix}{relative_path}"
                        storage.save_output_file(storage_key, file_path_obj.read_bytes())
                        logger.debug(f"Uploaded output file: {storage_key}")
                
                # Build images_base64 list for JSON response
                images_list = []
                try:
                    if image_dir.exists():
                        return_images = os.getenv('MINERU_RETURN_IMAGES_BASE64', 'true').lower() == 'true'
                        if return_images:
                            import base64
                            import mimetypes
                            for img_path in sorted(image_dir.iterdir()):
                                if not img_path.is_file():
                                    continue
                                try:
                                    with open(img_path, 'rb') as img_file:
                                        img_data = img_file.read()
                                    mime_type, _ = mimetypes.guess_type(str(img_path))
                                    if not mime_type or not mime_type.startswith('image/'):
                                        ext = img_path.suffix.lower()
                                        mime_type = MIME_TYPE_MAP.get(ext, 'image/png')
                                    data_url = f"data:{mime_type};base64,{base64.b64encode(img_data).decode('utf-8')}"
                                    images_list.append({
                                        'filename': img_path.name,
                                        'mime_type': mime_type,
                                        'size_bytes': len(img_data),
                                        'data_url': data_url,
                                    })
                                except Exception as e:
                                    logger.warning(f"Failed to build base64 for image {img_path}: {e}")
                except Exception as e:
                    logger.warning(f"Failed to enumerate images for task {task_id}: {e}")
                
                # Collect JSON file paths (if they exist)
                json_files = {}
                if parse_method == 'MinerU':
                    # Find JSON files generated by MinerU
                    base_name = Path(file_name).stem
                    auto_dir = output_path / base_name / "auto"
                    
                    content_list_json = auto_dir / f"{base_name}_content_list.json"
                    
                    if content_list_json.exists():
                        # Upload JSON file to storage
                        json_storage_key = f"{output_key_prefix}{base_name}/auto/{content_list_json.name}"
                        storage.save_output_file(json_storage_key, content_list_json.read_bytes())
                        json_files['content_list_json'] = json_storage_key
                
                # Check if markdown content contains Base64 images
                has_base64_images = 'data:image' in md_content
                
        finally:
            # Clean up temporary input file
            try:
                if local_input_path.exists() and str(local_input_path) != file_path:
                    local_input_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup local temp file {local_input_path}: {e}")
            
            # Clean up temporary file in storage
            try:
                storage.delete_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup storage temp file {file_path}: {e}")
        
        # Return result
        result = {
            'status': 'completed',
            'file_name': file_name,
            'backend': backend,
            'parse_method': parse_method,
            'completed_at': datetime.now().isoformat(),
            'data': {
                'content': md_content,
                'images_uploaded': upload_images,
                'images_as_base64': has_base64_images,
                'has_images': len(images_list) > 0,
                'images': images_list
            }
        }
        
        # If JSON files exist, add them to result
        if json_files:
            result['json_files'] = json_files
        
        logger.info(f"✅ Task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.exception(f"❌ Task {task_id} failed")
        
        # Clean up temporary files
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp file {file_path}: {cleanup_error}")
        
        return {
            'status': 'failed',
            'file_name': file_name,
            'backend': backend,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'completed_at': datetime.now().isoformat()
        }


def _parse_with_mineru(
    file_path: Path,
    file_name: str,
    task_id: str,
    backend: str,
    options: dict,
    output_path: Path
) -> dict:
    """Parse PDF and image formats using MinerU"""
    if not MINERU_AVAILABLE:
        raise RuntimeError("MinerU is not available. Please install it.")
    
    logger.info(f"📄 Using MinerU to parse: {file_name}")
    logger.debug(f"MinerU options: {options}")

    try:
        # Read file
        pdf_bytes = read_fn(file_path)
        
        # Enable only content_list output
        f_dump_content_list = True
        logger.info(f"🔧 JSON output options: content_list={f_dump_content_list}")
        
        # Execute parsing
        with pypdfium2_lock:
            do_parse(
                output_dir=str(output_path),
                pdf_file_names=[Path(file_name).stem],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=[options.get('lang', 'ch')],
                backend=backend,
                parse_method=options.get('method', 'auto'),
                formula_enable=options.get('formula_enable', True),
                table_enable=options.get('table_enable', True), 
            # JSON output options
            f_dump_content_list=f_dump_content_list,
        )
        
        return {'parser': 'MinerU', 'success': True}
        
    finally:
        # Clean up memory
        try:
            clean_memory()
        except Exception as e:
            logger.debug(f"Memory cleanup failed for task {task_id}: {e}")
        try:
            del pdf_bytes
        except Exception:
            pass
        try:
            gc.collect()
        except Exception:
            pass
        try:
            gc.collect()
        except Exception:
            pass


def _parse_with_markitdown(
    file_path: Path,
    file_name: str,
    output_path: Path
) -> dict:
    """Parse documents using MarkItDown"""
    if not MARKITDOWN_AVAILABLE:
        raise RuntimeError("MarkItDown is not available. Please install it: pip install markitdown")
    
    logger.info(f"📊 Using MarkItDown to parse: {file_name}")
    
    # Create MarkItDown instance
    markitdown = MarkItDown()
    
    # Convert document using markitdown
    result = markitdown.convert(str(file_path))
    
    # Save as markdown file
    output_file = output_path / f"{Path(file_name).stem}.md"
    output_file.write_text(result.text_content, encoding='utf-8')
    
    logger.info(f"📝 Markdown saved to: {output_file}")
    
    return {'parser': 'MarkItDown', 'success': True}


# Task status query helper function
def get_task_result(task_id: str, upload_images: bool = False) -> Dict[str, Any]:
    """
    Query task result (compatible with original MinerU API format)
    
    Args:
        task_id: Celery task ID
        upload_images: Whether to upload images to MinIO
        
    Returns:
        dict: Task status and result information, compatible with original API format
    """
    try:
        # Get Celery task result
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        # Map Celery status to original API status
        status_mapping = {
            'PENDING': 'pending',
            'STARTED': 'processing', 
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
            'RETRY': 'processing',
            'REVOKED': 'cancelled'
        }
        
        api_status = status_mapping.get(result.status, result.status.lower())
        
        # Build base response (compatible with original API format)
        response = {
            'success': True,
            'task': {
                'task_id': task_id,
                'status': api_status,
                'created_at': None,  # Celery does not directly provide creation time
                'started_at': None,
                'completed_at': None,
                'file_name': None,
                'backend': None,
                'result_path': None,
                'error_message': None,
                'retry_count': getattr(result, 'retries', 0)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        if result.successful():
            # Task completed successfully
            task_result = result.result or {}
            response['task'].update({
                'result_path': task_result.get('result_path'),
                'file_name': task_result.get('file_name'),
                'backend': task_result.get('backend'),
                'completed_at': task_result.get('completed_at')
            })
            
            # If Markdown content exists, add it to response
            if 'data' in task_result and 'content' in task_result['data']:
                response['markdown_content'] = task_result['data']['content']
                response['images'] = task_result['data'].get('images', [])
            
            # If JSON file paths exist, add them to response and try to embed JSON content
            if 'json_files' in task_result:
                response['json_files'] = task_result['json_files']

                # Safely read JSON file content and embed in response for direct use by upstream
                def _safe_load_json(path_str: Optional[str]) -> Optional[Dict[str, Any]]:
                    try:
                        if not path_str:
                            return None
                        p = Path(path_str)
                        if not p.exists():
                            return None
                        with open(p, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except Exception:
                        return None

                content_list_path = task_result['json_files'].get('content_list_json')
                content_list = _safe_load_json(content_list_path)

                # Only add to response body if successfully read
                if content_list is not None:
                    response['content_list'] = content_list
                
            # If image upload needs to be reprocessed
            if upload_images and 'data' in task_result and not task_result['data'].get('images_uploaded', False):
                # Reprocess image upload logic
                pass
                
        elif result.failed():
            # Task failed
            error_info = result.result if result.result else result.traceback
            response['task'].update({
                'error_message': str(error_info) if error_info else 'Unknown error',
                'completed_at': datetime.now().isoformat()
            })
            
        elif api_status == 'processing':
            # Task in progress, try to get progress information
            if hasattr(result, 'info') and result.info:
                progress_info = result.info
                if isinstance(progress_info, dict):
                    response['task'].update({
                        'file_name': progress_info.get('file_name'),
                        'backend': progress_info.get('backend'),
                        'started_at': progress_info.get('started_at')
                    })
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        return {
            'success': False,
            'error': f'Failed to query task: {str(e)}',
            'task': {
                'task_id': task_id,
                'status': 'unknown',
                'error_message': str(e)
            },
            'timestamp': datetime.now().isoformat()
        }


def get_queue_stats():
    """
    Get queue statistics (compatible with original API format)
    
    Returns:
        dict: Queue statistics
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active_tasks = inspect.active() or {}
        active_count = sum(len(tasks) for tasks in active_tasks.values())
        
        # Get waiting tasks
        scheduled_tasks = inspect.scheduled() or {}
        pending_count = sum(len(tasks) for tasks in scheduled_tasks.values())
        
        # Get reserved tasks
        reserved_tasks = inspect.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved_tasks.values())
        
        return {
            'success': True,
            'stats': {
                'pending': pending_count + reserved_count,
                'processing': active_count,
                'completed': 0,  # Celery does not save completed task statistics
                'failed': 0,     # Celery does not save failed task statistics
                'total_active': active_count,
                'total_scheduled': pending_count
            },
            'workers': {
                'active_workers': len(active_tasks),
                'total_workers': len(inspect.stats() or {})
            },
            'timestamp': datetime.now().isoformat(),
            'note': 'Completed/failed counts not available in Celery. Only active tasks are tracked.'
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': {
                'pending': 0,
                'processing': 0, 
                'completed': 0,
                'failed': 0
            },
            'timestamp': datetime.now().isoformat()
        }


def list_tasks(status_filter: str = None, limit: int = 100):
    """
    Get task list (compatible with original API format)
    
    Args:
        status_filter: Status filter
        limit: Return count limit
        
    Returns:
        dict: Task list
    """
    try:
        inspect = celery_app.control.inspect()
        tasks = []
        
        # Get active tasks
        if not status_filter or status_filter == 'processing':
            active_tasks = inspect.active() or {}
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks:
                    task_info = {
                        'task_id': task['id'],
                        'status': 'processing',
                        'worker_id': worker,
                        'file_name': task.get('kwargs', {}).get('file_name'),
                        'backend': task.get('kwargs', {}).get('backend'),
                        'started_at': task.get('time_start'),
                        'created_at': None,
                        'priority': 0
                    }
                    tasks.append(task_info)
        
        # Get waiting tasks
        if not status_filter or status_filter == 'pending':
            scheduled_tasks = inspect.scheduled() or {}
            for worker, worker_tasks in scheduled_tasks.items():
                for task in worker_tasks:
                    task_info = {
                        'task_id': task['request']['id'],
                        'status': 'pending',
                        'worker_id': None,
                        'file_name': task['request'].get('kwargs', {}).get('file_name'),
                        'backend': task['request'].get('kwargs', {}).get('backend'),
                        'created_at': None,
                        'started_at': None,
                        'priority': task.get('priority', 0),
                        'eta': task.get('eta')
                    }
                    tasks.append(task_info)
        
        # Limit return count
        tasks = tasks[:limit]
        
        return {
            'success': True,
            'tasks': tasks,
            'count': len(tasks),
            'limit': limit,
            'status_filter': status_filter,
            'timestamp': datetime.now().isoformat(),
            'note': 'Only active and scheduled tasks are shown. Historical tasks are not stored by default.'
        }
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return {
            'success': False,
            'error': str(e),
            'tasks': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    print("🚀 Starting MinerU Celery Worker...")
    print(f"🏷️  Worker Name: {celeryconfig.WORKER_NAME}")
    print(f"📋 Queue: {celeryconfig.task_default_queue}")
    print(f"🔗 Broker: {celeryconfig.broker_url}")
    print(f"💾 Backend: {celeryconfig.result_backend}")
    print(f"⚙️  Concurrency: {celeryconfig.WORKER_CONCURRENCY}")
    worker_pool = celeryconfig.WORKER_POOL or 'prefork'
    print(f"🧵 Pool: {worker_pool}")
    print(f"⚠️  Note: This worker does NOT provide API")
    print()

    worker_args = [
        'worker',
        '--loglevel=INFO',
        '-n', f'{celeryconfig.WORKER_NAME}@%h',
        '-Q', celeryconfig.task_default_queue,
        f'--concurrency={celeryconfig.WORKER_CONCURRENCY}',
        f'--max-memory-per-child={celeryconfig.worker_max_memory_per_child}'
    ]

    if celeryconfig.WORKER_POOL:
        worker_args.append(f'--pool={celeryconfig.WORKER_POOL}')

    celery_app.worker_main(worker_args)
