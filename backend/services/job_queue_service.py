"""
Job Queue Service for background job processing.

Handles job queuing, priority-based execution, and retry logic.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from database import execute_query, execute_write

logger = logging.getLogger(__name__)


class JobQueueService:
    """Service for managing background jobs."""
    
    def __init__(self):
        self._job_handlers: Dict[str, Callable] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type."""
        self._job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")
    
    def enqueue(
        self,
        job_type: str,
        job_parameters: Dict = None,
        priority: int = 5,
        max_retries: int = 3
    ) -> int:
        """Add a job to the queue."""
        return execute_write("""
            INSERT INTO background_jobs 
            (job_type, job_parameters, priority, max_retries, status, queued_at)
            VALUES (?, ?, ?, ?, 'queued', CURRENT_TIMESTAMP)
        """, (
            job_type,
            json.dumps(job_parameters or {}),
            priority,
            max_retries
        ))
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get a specific job."""
        jobs = execute_query("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
        return jobs[0] if jobs else None
    
    def get_queue(self, status: str = None, limit: int = 50) -> List[Dict]:
        """Get jobs from the queue."""
        query = "SELECT * FROM background_jobs"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY priority DESC, queued_at ASC LIMIT ?"
        params.append(limit)
        
        return execute_query(query, tuple(params))
    
    def cancel_job(self, job_id: int) -> bool:
        """Cancel a pending job."""
        job = self.get_job(job_id)
        if not job or job['status'] not in ('queued', 'running'):
            return False
        
        execute_write(
            "UPDATE background_jobs SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (job_id,)
        )
        return True
    
    def retry_job(self, job_id: int) -> bool:
        """Retry a failed job."""
        job = self.get_job(job_id)
        if not job or job['status'] != 'failed':
            return False
        
        execute_write(
            "UPDATE background_jobs SET status = 'queued', retry_count = retry_count + 1 WHERE id = ?",
            (job_id,)
        )
        return True
    
    def clear_completed(self, older_than_days: int = 7) -> int:
        """Clear completed jobs older than specified days."""
        cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        execute_write(
            "DELETE FROM background_jobs WHERE status IN ('completed', 'cancelled') AND completed_at < ?",
            (cutoff,)
        )
        return True
    
    async def process_next(self) -> Optional[Dict]:
        """Process the next job in the queue."""
        # Get next queued job (highest priority, oldest first)
        jobs = execute_query("""
            SELECT * FROM background_jobs 
            WHERE status = 'queued'
            ORDER BY priority DESC, queued_at ASC
            LIMIT 1
        """)
        
        if not jobs:
            return None
        
        job = jobs[0]
        job_id = job['id']
        job_type = job['job_type']
        
        # Mark as running
        started_at = datetime.now()
        execute_write(
            "UPDATE background_jobs SET status = 'running', started_at = ? WHERE id = ?",
            (started_at.isoformat(), job_id)
        )
        
        result = None
        error_details = None
        status = 'completed'
        
        try:
            handler = self._job_handlers.get(job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job_type}")
            
            params = json.loads(job.get('job_parameters') or '{}')
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                result = handler(params)
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            error_details = str(e)
            
            # Check if we should retry
            if job['retry_count'] < job['max_retries']:
                status = 'queued'
                execute_write(
                    "UPDATE background_jobs SET status = 'queued', retry_count = retry_count + 1 WHERE id = ?",
                    (job_id,)
                )
                return {"job_id": job_id, "status": "retry_scheduled", "error": str(e)}
            else:
                status = 'failed'
        
        # Update job
        completed_at = datetime.now()
        execute_write("""
            UPDATE background_jobs 
            SET status = ?, completed_at = ?, result_data = ?, error_details = ?
            WHERE id = ?
        """, (
            status,
            completed_at.isoformat(),
            json.dumps(result) if result else None,
            error_details,
            job_id
        ))
        
        return {"job_id": job_id, "status": status, "result": result}
    
    async def run_worker_loop(self, check_interval: int = 5):
        """Worker loop that processes jobs from the queue."""
        self._running = True
        logger.info("Job queue worker started")
        
        while self._running:
            try:
                result = await self.process_next()
                if result:
                    logger.info(f"Processed job: {result}")
                    # If we processed a job, check immediately for more
                    continue
            except Exception as e:
                logger.error(f"Job worker error: {e}")
            
            await asyncio.sleep(check_interval)
        
        logger.info("Job queue worker stopped")
    
    def start(self):
        """Start the job queue worker."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_worker_loop())
            logger.info("Job queue worker started")
    
    def stop(self):
        """Stop the job queue worker."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Job queue worker stopped")


# Import timedelta for clear_completed
from datetime import timedelta

# Singleton instance
_job_queue = None


def get_job_queue() -> JobQueueService:
    """Get the singleton job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueueService()
    return _job_queue
