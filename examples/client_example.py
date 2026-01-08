"""
Document Processing Client Example

Demonstrates how to use Python client to submit tasks and query status
"""
import asyncio
import aiohttp
from pathlib import Path
from loguru import logger
import time
from typing import Dict


class DocumentProcessorClient:
    """Document processing client"""
    
    def __init__(self, api_url='http://localhost:8000'):
        self.api_url = api_url
        self.base_url = f"{api_url}/api/v1"
    
    async def submit_task(
        self,
        session: aiohttp.ClientSession,
        file_path: str,
        backend: str = 'pipeline',
        lang: str = 'ch',
        method: str = 'auto',
        formula_enable: bool = True,
        table_enable: bool = True,
        priority: int = 0
    ) -> Dict:
        """
        Submit task
        
        Args:
            session: aiohttp session
            file_path: File path
            backend: Processing backend
            lang: Language
            method: Parsing method
            formula_enable: Whether to enable formula recognition
            table_enable: Whether to enable table recognition
            priority: Priority
            
        Returns:
            Response dictionary containing task_id
        """
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=Path(file_path).name)
            data.add_field('backend', backend)
            data.add_field('lang', lang)
            data.add_field('method', method)
            data.add_field('formula_enable', str(formula_enable).lower())
            data.add_field('table_enable', str(table_enable).lower())
            data.add_field('priority', str(priority))
            
            async with session.post(f'{self.base_url}/tasks/submit', data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Submitted: {file_path} -> Task ID: {result['task_id']}")
                    return result
                else:
                    error = await resp.text()
                    logger.error(f"❌ Failed to submit {file_path}: {error}")
                    return {'success': False, 'error': error}
    
    async def get_task_status(self, session: aiohttp.ClientSession, task_id: str) -> Dict:
        """
        Query task status
        
        Args:
            session: aiohttp session
            task_id: Task ID
            
        Returns:
            Task status dictionary
        """
        async with session.get(f'{self.base_url}/tasks/{task_id}') as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {'success': False, 'error': 'Task not found'}
    
    async def wait_for_task(
        self,
        session: aiohttp.ClientSession,
        task_id: str,
        timeout: int = 600,
        poll_interval: int = 2
    ) -> Dict:
        """
        Wait for task completion
        
        Args:
            session: aiohttp session
            task_id: Task ID
            timeout: Timeout in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final task status
        """
        start_time = time.time()
        
        while True:
            status = await self.get_task_status(session, task_id)
            
            if not status.get('success'):
                logger.error(f"❌ Failed to get status for task {task_id}")
                return status
            
            task_status = status.get('status')
            
            if task_status == 'completed':
                logger.info(f"✅ Task {task_id} completed!")
                logger.info(f"   Output: {status.get('result_path')}")
                return status
            
            elif task_status == 'failed':
                logger.error(f"❌ Task {task_id} failed!")
                logger.error(f"   Error: {status.get('error_message')}")
                return status
            
            elif task_status == 'cancelled':
                logger.warning(f"⚠️  Task {task_id} was cancelled")
                return status
            
            # Check timeout
            if time.time() - start_time > timeout:
                logger.error(f"⏱️  Task {task_id} timeout after {timeout}s")
                return {'success': False, 'error': 'timeout'}
            
            # Wait before continuing polling
            await asyncio.sleep(poll_interval)
    
    async def get_queue_stats(self, session: aiohttp.ClientSession) -> Dict:
        """Get queue statistics"""
        async with session.get(f'{self.base_url}/queue/stats') as resp:
            return await resp.json()
    
    async def cancel_task(self, session: aiohttp.ClientSession, task_id: str) -> Dict:
        """Cancel task"""
        async with session.delete(f'{self.base_url}/tasks/{task_id}') as resp:
            return await resp.json()


async def example_single_task():
    """Example 1: Submit a single task and wait for completion"""
    logger.info("=" * 60)
    logger.info("Example 1: Submit a single task")
    logger.info("=" * 60)
    
    client = DocumentProcessorClient()
    
    async with aiohttp.ClientSession() as session:
        # Submit task
        result = await client.submit_task(
            session,
            file_path='../../demo/pdfs/demo1.pdf',
            backend='pipeline',
            lang='ch',
            formula_enable=True,
            table_enable=True
        )
        
        if result.get('success'):
            task_id = result['task_id']
            
            # Wait for completion
            logger.info(f"⏳ Waiting for task {task_id} to complete...")
            final_status = await client.wait_for_task(session, task_id)
            
            return final_status


async def example_batch_tasks():
    """Example 2: Submit multiple tasks in batch and wait concurrently"""
    logger.info("=" * 60)
    logger.info("Example 2: Submit multiple tasks in batch")
    logger.info("=" * 60)
    
    client = DocumentProcessorClient()
    
    # Prepare task list
    files = [
        '../../demo/pdfs/demo1.pdf',
        '../../demo/pdfs/demo2.pdf',
        '../../demo/pdfs/demo3.pdf',
    ]
    
    async with aiohttp.ClientSession() as session:
        # Submit all tasks concurrently
        logger.info(f"📤 Submitting {len(files)} tasks...")
        submit_tasks = [
            client.submit_task(session, file) 
            for file in files
        ]
        results = await asyncio.gather(*submit_tasks)
        
        # Extract task_ids
        task_ids = [r['task_id'] for r in results if r.get('success')]
        logger.info(f"✅ Submitted {len(task_ids)} tasks successfully")
        
        # Wait for all tasks to complete concurrently
        logger.info(f"⏳ Waiting for all tasks to complete...")
        wait_tasks = [
            client.wait_for_task(session, task_id) 
            for task_id in task_ids
        ]
        final_results = await asyncio.gather(*wait_tasks)
        
        # Count results
        completed = sum(1 for r in final_results if r.get('status') == 'completed')
        failed = sum(1 for r in final_results if r.get('status') == 'failed')
        
        logger.info("=" * 60)
        logger.info(f"📊 Results: {completed} completed, {failed} failed")
        logger.info("=" * 60)
        
        return final_results


async def example_priority_tasks():
    """Example 3: Using priority queue"""
    logger.info("=" * 60)
    logger.info("Example 3: Priority queue")
    logger.info("=" * 60)
    
    client = DocumentProcessorClient()
    
    async with aiohttp.ClientSession() as session:
        # Submit low priority task
        low_priority = await client.submit_task(
            session,
            file_path='../../demo/pdfs/demo1.pdf',
            priority=0
        )
        logger.info(f"📝 Low priority task: {low_priority['task_id']}")
        
        # Submit high priority task
        high_priority = await client.submit_task(
            session,
            file_path='../../demo/pdfs/demo2.pdf',
            priority=10
        )
        logger.info(f"🔥 High priority task: {high_priority['task_id']}")
        
        # High priority tasks will be processed first
        logger.info("⏳ High priority tasks will be processed first...")


async def example_queue_monitoring():
    """Example 4: Monitor queue status"""
    logger.info("=" * 60)
    logger.info("Example 4: Monitor queue status")
    logger.info("=" * 60)
    
    client = DocumentProcessorClient()
    
    async with aiohttp.ClientSession() as session:
        # Get queue statistics
        stats = await client.get_queue_stats(session)
        
        logger.info("📊 Queue Statistics:")
        logger.info(f"   Total: {stats.get('total', 0)}")
        for status, count in stats.get('stats', {}).items():
            logger.info(f"   {status:12s}: {count}")


async def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
    else:
        example = 'all'
    
    try:
        if example == 'single' or example == 'all':
            await example_single_task()
            print()
        
        if example == 'batch' or example == 'all':
            await example_batch_tasks()
            print()
        
        if example == 'priority' or example == 'all':
            await example_priority_tasks()
            print()
        
        if example == 'monitor' or example == 'all':
            await example_queue_monitoring()
            print()
            
    except Exception as e:
        logger.error(f"Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    """
    Usage:
    
    # Run all examples
    python client_example.py
    
    # Run specific example
    python client_example.py single
    python client_example.py batch
    python client_example.py priority
    python client_example.py monitor
    """
    asyncio.run(main())

