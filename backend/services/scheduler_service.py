"""
Scheduler Service for background task scheduling and execution.

Handles cron expression parsing, task scheduling, and execution.
"""

import json
import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from database import execute_query, execute_write

logger = logging.getLogger(__name__)


@dataclass
class CronExpression:
    """Parsed cron expression."""
    minute: str
    hour: str
    day_of_month: str
    month: str
    day_of_week: str


def parse_cron(expression: str) -> CronExpression:
    """Parse a cron expression into components."""
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expression}. Expected 5 parts.")
    
    return CronExpression(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month=parts[3],
        day_of_week=parts[4]
    )


def _match_cron_field(value: int, field: str, max_val: int) -> bool:
    """Check if a value matches a cron field expression."""
    if field == '*':
        return True
    
    # Handle */n (step values)
    if field.startswith('*/'):
        step = int(field[2:])
        return value % step == 0
    
    # Handle ranges (e.g., 1-5)
    if '-' in field:
        start, end = map(int, field.split('-'))
        return start <= value <= end
    
    # Handle lists (e.g., 1,3,5)
    if ',' in field:
        values = [int(v) for v in field.split(',')]
        return value in values
    
    # Simple numeric match
    return value == int(field)


def get_next_run_time(cron_expr: str, from_time: datetime = None) -> datetime:
    """Calculate the next run time from a cron expression."""
    if from_time is None:
        from_time = datetime.now()
    
    cron = parse_cron(cron_expr)
    
    # Start from next minute
    next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
    
    # Iterate up to 1 year to find next match
    max_iterations = 525600  # Minutes in a year
    
    for _ in range(max_iterations):
        if (
            _match_cron_field(next_time.minute, cron.minute, 59) and
            _match_cron_field(next_time.hour, cron.hour, 23) and
            _match_cron_field(next_time.day, cron.day_of_month, 31) and
            _match_cron_field(next_time.month, cron.month, 12) and
            _match_cron_field(next_time.weekday(), cron.day_of_week, 6)
        ):
            return next_time
        
        next_time += timedelta(minutes=1)
    
    raise ValueError(f"Could not find next run time for: {cron_expr}")


class SchedulerService:
    """Service for managing scheduled tasks."""
    
    def __init__(self):
        self._task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type."""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    def get_scheduled_tasks(self, enabled_only: bool = False) -> List[Dict]:
        """Get all scheduled tasks."""
        query = "SELECT * FROM scheduled_tasks"
        if enabled_only:
            query += " WHERE is_enabled = 1"
        query += " ORDER BY next_run_at ASC"
        return execute_query(query)
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """Get a specific scheduled task."""
        tasks = execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
        return tasks[0] if tasks else None
    
    def create_task(
        self,
        task_type: str,
        task_name: str,
        schedule_expression: str,
        task_parameters: Dict = None,
        is_enabled: bool = True
    ) -> int:
        """Create a new scheduled task."""
        # Validate cron expression
        next_run = get_next_run_time(schedule_expression)
        
        return execute_write("""
            INSERT INTO scheduled_tasks 
            (task_type, task_name, task_parameters, schedule_expression, next_run_at, is_enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            task_type,
            task_name,
            json.dumps(task_parameters or {}),
            schedule_expression,
            next_run.isoformat(),
            1 if is_enabled else 0
        ))
    
    def update_task(self, task_id: int, updates: Dict) -> bool:
        """Update a scheduled task."""
        allowed_fields = ['task_name', 'task_parameters', 'schedule_expression', 'is_enabled']
        fields = []
        values = []
        
        for key, value in updates.items():
            if key in allowed_fields:
                if key == 'task_parameters':
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        # If schedule changed, recalculate next run
        if 'schedule_expression' in updates:
            next_run = get_next_run_time(updates['schedule_expression'])
            fields.append("next_run_at = ?")
            values.append(next_run.isoformat())
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        execute_write(f"UPDATE scheduled_tasks SET {', '.join(fields)} WHERE id = ?", tuple(values))
        return True
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a scheduled task."""
        execute_write("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        return True
    
    def toggle_task(self, task_id: int, enabled: bool) -> bool:
        """Enable or disable a task."""
        execute_write(
            "UPDATE scheduled_tasks SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if enabled else 0, task_id)
        )
        return True
    
    async def trigger_task(self, task_id: int) -> Dict:
        """Manually trigger a task execution."""
        task = self.get_task(task_id)
        if not task:
            return {"error": "Task not found"}
        
        return await self._execute_task(task)
    
    async def _execute_task(self, task: Dict) -> Dict:
        """Execute a scheduled task."""
        task_id = task['id']
        task_type = task['task_type']
        
        # Create execution record
        started_at = datetime.now()
        execution_id = execute_write("""
            INSERT INTO task_executions (scheduled_task_id, started_at, status)
            VALUES (?, ?, 'running')
        """, (task_id, started_at.isoformat()))
        
        # Log activity
        activity_id = execute_write("""
            INSERT INTO agent_activity_log (activity_type, activity_description, triggered_by, started_at)
            VALUES ('scheduled_task', ?, 'schedule', ?)
        """, (f"Executing {task['task_name']}", started_at.isoformat()))
        
        result = {"status": "unknown", "items_affected": 0}
        error_details = None
        
        try:
            handler = self._task_handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")
            
            params = json.loads(task.get('task_parameters') or '{}')
            
            # Execute handler (may be async or sync)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                result = handler(params)
            
            status = 'completed'
            
        except Exception as e:
            logger.error(f"Task execution failed for {task_type}: {e}")
            error_details = str(e)
            status = 'failed'
            result = {"error": str(e)}
            
            # Increment failure count
            execute_write(
                "UPDATE scheduled_tasks SET failure_count = failure_count + 1 WHERE id = ?",
                (task_id,)
            )
        
        # Update execution record
        completed_at = datetime.now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        execute_write("""
            UPDATE task_executions 
            SET completed_at = ?, status = ?, result_summary = ?, error_details = ?, items_affected = ?
            WHERE id = ?
        """, (
            completed_at.isoformat(),
            status,
            json.dumps(result),
            error_details,
            result.get('items_affected', 0),
            execution_id
        ))
        
        # Update scheduled task
        next_run = get_next_run_time(task['schedule_expression'])
        execute_write("""
            UPDATE scheduled_tasks 
            SET last_run_at = ?, last_run_status = ?, last_run_duration_ms = ?, next_run_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            completed_at.isoformat(),
            'success' if status == 'completed' else 'failed',
            duration_ms,
            next_run.isoformat(),
            task_id
        ))
        
        # Update activity log
        execute_write("""
            UPDATE agent_activity_log 
            SET completed_at = ?, items_affected = ?
            WHERE id = ?
        """, (completed_at.isoformat(), result.get('items_affected', 0), activity_id))
        
        return result
    
    async def run_scheduler_loop(self, check_interval: int = 60):
        """Main scheduler loop that checks and executes due tasks."""
        self._running = True
        logger.info("Scheduler loop started")
        
        while self._running:
            try:
                await self._check_and_execute_due_tasks()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            await asyncio.sleep(check_interval)
        
        logger.info("Scheduler loop stopped")
    
    async def _check_and_execute_due_tasks(self):
        """Check for and execute tasks that are due."""
        now = datetime.now().isoformat()
        
        due_tasks = execute_query("""
            SELECT * FROM scheduled_tasks 
            WHERE is_enabled = 1 AND next_run_at <= ?
            ORDER BY next_run_at ASC
        """, (now,))
        
        for task in due_tasks:
            logger.info(f"Executing due task: {task['task_name']}")
            await self._execute_task(task)
    
    def start(self):
        """Start the scheduler."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_scheduler_loop())
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduler stopped")
    
    def get_executions(self, task_id: int = None, limit: int = 20) -> List[Dict]:
        """Get task execution history."""
        query = "SELECT * FROM task_executions"
        params = []
        
        if task_id:
            query += " WHERE scheduled_task_id = ?"
            params.append(task_id)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        return execute_query(query, tuple(params))


# Singleton instance
_scheduler = None


def get_scheduler() -> SchedulerService:
    """Get the singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler
