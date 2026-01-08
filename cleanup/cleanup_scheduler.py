#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU Cleanup Scheduler
Scheduled cleanup service running in container, uses schedule library for scheduled tasks
"""
import os
import sys
import time
import signal
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project path to import shared module
# cleanup_scheduler.py is located in cleanup/ directory, needs to access parent directory's shared module
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import schedule
except ImportError:
    print("Error: schedule library is required")
    print("Please run: pip install schedule")
    sys.exit(1)

import argparse
import subprocess


class CleanupScheduler:
    """Cleanup task scheduler"""
    
    def __init__(self, cleanup_hours: int = 24, extra_hours: int = 2):
        """
        Initialize scheduler
        
        Args:
            cleanup_hours: Cleanup task execution interval (hours)
            extra_hours: Extra retention time (hours)
        """
        self.cleanup_hours = cleanup_hours
        self.extra_hours = extra_hours
        self.running = True
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle exit signal"""
        print(f"\nReceived signal {signum}, stopping scheduler...")
        self.running = False
    
    def _run_cleanup(self):
        """Execute cleanup task"""
        print(f"\n{'='*60}")
        print(f"Executing scheduled cleanup task - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Check storage type to determine cleanup strategy
        storage_type = os.getenv('MINERU_STORAGE_TYPE', 'local').lower()
        
        # Call cleanup script
        script_path = Path(__file__).parent / 'cleanup_outputs.py'
        cmd = [sys.executable, str(script_path), '--extra-hours', str(self.extra_hours)]
        
        # If using S3 storage, only clean output files (temporary files handled by S3 lifecycle policy)
        if storage_type == 's3':
            cmd.append('--output-only')
            print("Detected S3 storage mode, only cleaning output files (temporary files handled by S3 lifecycle policy)")
        else:
            print("Detected local storage mode, cleaning temporary files and output files")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=False,
                text=True
            )
            if result.returncode == 0:
                print("Cleanup task executed successfully")
            else:
                print(f"Cleanup task execution failed, exit code: {result.returncode}")
        except Exception as e:
            print(f"Cleanup task execution failed: {e}")
    
    def start(self):
        """Start scheduler"""
        # Set scheduled task
        schedule.every(self.cleanup_hours).hours.do(self._run_cleanup)
        
        # Execute once immediately (optional)
        print(f"Cleanup scheduler started")
        print(f"Cleanup interval: every {self.cleanup_hours} hours")
        print(f"Extra retention time: {self.extra_hours} hours")
        print(f"First cleanup will execute in {self.cleanup_hours} hours")
        print("Press Ctrl+C to stop scheduler\n")
        
        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        print("\nScheduler stopped")


def main():
    parser = argparse.ArgumentParser(
        description='MinerU Cleanup Task Scheduler',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=24,
        help='Cleanup task execution interval (hours, default: 24)'
    )
    parser.add_argument(
        '--extra-hours',
        type=int,
        default=2,
        help='Extra retention time (hours, default: 2)'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Execute cleanup task once only, do not start scheduler'
    )
    
    args = parser.parse_args()
    
    if args.run_once:
        # Execute once only
        print("Executing single cleanup task...")
        script_path = Path(__file__).parent / 'cleanup_outputs.py'
        
        # Check storage type to determine cleanup strategy
        storage_type = os.getenv('MINERU_STORAGE_TYPE', 'local').lower()
        cmd = [sys.executable, str(script_path), '--extra-hours', str(args.extra_hours)]
        
        # If using S3 storage, only clean output files (temporary files handled by S3 lifecycle policy)
        if storage_type == 's3':
            cmd.append('--output-only')
            print("Detected S3 storage mode, only cleaning output files")
        else:
            print("Detected local storage mode, cleaning temporary files and output files")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=False,
                text=True
            )
            sys.exit(result.returncode)
        except Exception as e:
            print(f"Cleanup task execution failed: {e}")
            sys.exit(1)
    else:
        # Start scheduler
        scheduler = CleanupScheduler(
            cleanup_hours=args.interval,
            extra_hours=args.extra_hours
        )
        scheduler.start()


if __name__ == '__main__':
    main()

