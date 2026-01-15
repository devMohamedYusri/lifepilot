"""
Scheduler API endpoints for background task management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from services.scheduler_service import get_scheduler, get_next_run_time
from services.job_queue_service import get_job_queue
from services.proactive_service import get_activity_summary, PROACTIVE_HANDLERS

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


# === Pydantic Models ===

class ScheduledTaskCreate(BaseModel):
    task_type: str
    task_name: str
    schedule_expression: str
    task_parameters: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = True


class ScheduledTaskUpdate(BaseModel):
    task_name: Optional[str] = None
    schedule_expression: Optional[str] = None
    task_parameters: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class BackgroundSettingsUpdate(BaseModel):
    scheduler_enabled: Optional[bool] = None
    job_queue_enabled: Optional[bool] = None


# === Scheduled Tasks Endpoints ===

@router.get("/tasks")
async def get_scheduled_tasks(enabled_only: bool = False):
    """Get all scheduled tasks."""
    scheduler = get_scheduler()
    tasks = scheduler.get_scheduled_tasks(enabled_only=enabled_only)
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/tasks")
async def create_scheduled_task(task: ScheduledTaskCreate):
    """Create a new scheduled task."""
    try:
        scheduler = get_scheduler()
        task_id = scheduler.create_task(
            task_type=task.task_type,
            task_name=task.task_name,
            schedule_expression=task.schedule_expression,
            task_parameters=task.task_parameters,
            is_enabled=task.is_enabled
        )
        return {"id": task_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_scheduled_task(task_id: int):
    """Get a specific scheduled task."""
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/tasks/{task_id}")
async def update_scheduled_task(task_id: int, updates: ScheduledTaskUpdate):
    """Update a scheduled task."""
    scheduler = get_scheduler()
    
    update_dict = updates.model_dump(exclude_none=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        scheduler.update_task(task_id, update_dict)
        return {"id": task_id, "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_scheduled_task(task_id: int):
    """Delete a scheduled task."""
    scheduler = get_scheduler()
    scheduler.delete_task(task_id)
    return {"id": task_id, "status": "deleted"}


@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, enabled: bool):
    """Enable or disable a task."""
    scheduler = get_scheduler()
    scheduler.toggle_task(task_id, enabled)
    return {"id": task_id, "enabled": enabled}


@router.post("/tasks/{task_id}/trigger")
async def trigger_task_now(task_id: int):
    """Manually trigger a task to run immediately."""
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = await scheduler.trigger_task(task_id)
    return {"id": task_id, "result": result}


@router.get("/tasks/{task_id}/executions")
async def get_task_executions(task_id: int, limit: int = Query(default=20, le=100)):
    """Get execution history for a task."""
    scheduler = get_scheduler()
    executions = scheduler.get_executions(task_id=task_id, limit=limit)
    return {"executions": executions, "count": len(executions)}


# === Job Queue Endpoints ===

@router.get("/jobs")
async def get_job_queue_status(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get jobs from the queue."""
    queue = get_job_queue()
    jobs = queue.get_queue(status=status, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
    """Get a specific job."""
    queue = get_job_queue()
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int):
    """Cancel a job."""
    queue = get_job_queue()
    success = queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job (already completed or not found)")
    return {"id": job_id, "status": "cancelled"}


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int):
    """Retry a failed job."""
    queue = get_job_queue()
    success = queue.retry_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot retry job (not failed or not found)")
    return {"id": job_id, "status": "queued"}


# === Activity Endpoints ===

@router.get("/activity")
async def get_activity(
    since: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get agent activity log."""
    from database import execute_query
    
    query = "SELECT * FROM agent_activity_log"
    params = []
    
    if since:
        query += " WHERE started_at >= ?"
        params.append(since)
    
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    
    activities = execute_query(query, tuple(params))
    return {"activities": activities, "count": len(activities)}


@router.get("/activity/summary")
async def get_activity_summary_endpoint(hours: int = Query(default=24, le=168)):
    """Get summarized activity report."""
    since = (datetime.now() - __import__('datetime').timedelta(hours=hours)).isoformat()
    summary = get_activity_summary(since=since)
    return summary


# === Settings Endpoints ===

@router.get("/settings")
async def get_background_settings():
    """Get background processing settings."""
    from database import execute_query
    
    settings = execute_query(
        "SELECT * FROM agent_settings WHERE category IN ('proactive', 'limits')"
    )
    
    scheduler = get_scheduler()
    queue = get_job_queue()
    
    return {
        "settings": {s['key']: s['value'] for s in settings},
        "scheduler_running": scheduler._running,
        "job_queue_running": queue._running,
        "available_task_types": list(PROACTIVE_HANDLERS.keys())
    }


@router.put("/settings")
async def update_background_settings(updates: BackgroundSettingsUpdate):
    """Update background processing settings."""
    scheduler = get_scheduler()
    queue = get_job_queue()
    
    if updates.scheduler_enabled is not None:
        if updates.scheduler_enabled:
            scheduler.start()
        else:
            scheduler.stop()
    
    if updates.job_queue_enabled is not None:
        if updates.job_queue_enabled:
            queue.start()
        else:
            queue.stop()
    
    return {
        "scheduler_running": scheduler._running,
        "job_queue_running": queue._running
    }


# === Utility Endpoints ===

@router.post("/cron/validate")
async def validate_cron_expression(expression: str):
    """Validate a cron expression and get next run time."""
    try:
        next_run = get_next_run_time(expression)
        return {
            "valid": True,
            "expression": expression,
            "next_run": next_run.isoformat()
        }
    except ValueError as e:
        return {
            "valid": False,
            "expression": expression,
            "error": str(e)
        }
