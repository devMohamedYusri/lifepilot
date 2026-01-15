"""Energy router for tracking and analyzing energy/focus."""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta

from database import execute_query, execute_write
from services.energy_service import (
    get_time_block, get_today_logs, get_recent_logs,
    calculate_averages, get_averages_by_time_block,
    analyze_patterns, get_best_time_for_task
)

router = APIRouter(prefix="/api/energy", tags=["energy"])


@router.post("/log")
async def create_energy_log(log: dict):
    """Log energy/focus check-in."""
    energy_level = log.get('energy_level')
    if not energy_level:
        raise HTTPException(status_code=400, detail="energy_level is required (1-5)")
    
    if not 1 <= energy_level <= 5:
        raise HTTPException(status_code=400, detail="energy_level must be between 1 and 5")
    
    logged_at = log.get('logged_at') or datetime.now().isoformat()
    time_block = log.get('time_block') or get_time_block()
    
    query = """
        INSERT INTO energy_logs (
            logged_at, time_block,
            energy_level, focus_level, mood_level, stress_level,
            sleep_hours, caffeine, exercise, meals_eaten,
            current_activity, location, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        logged_at, time_block,
        energy_level,
        log.get('focus_level'),
        log.get('mood_level'),
        log.get('stress_level'),
        log.get('sleep_hours'),
        log.get('caffeine', 0),
        log.get('exercise', 0),
        log.get('meals_eaten', 0),
        log.get('current_activity'),
        log.get('location'),
        log.get('notes'),
        datetime.now().isoformat()
    )
    
    log_id = execute_write(query, params)
    result = execute_query("SELECT * FROM energy_logs WHERE id = ?", (log_id,))
    return dict(result[0])


@router.post("/quick")
async def quick_log(log: dict):
    """Super quick energy/focus log (just energy + optional focus)."""
    energy = log.get('energy')
    if not energy:
        raise HTTPException(status_code=400, detail="energy is required (1-5)")
    
    logged_at = datetime.now().isoformat()
    time_block = get_time_block()
    
    query = """
        INSERT INTO energy_logs (logged_at, time_block, energy_level, focus_level, created_at)
        VALUES (?, ?, ?, ?, ?)
    """
    
    log_id = execute_write(query, (
        logged_at, time_block, energy, log.get('focus'), datetime.now().isoformat()
    ))
    
    result = execute_query("SELECT * FROM energy_logs WHERE id = ?", (log_id,))
    return dict(result[0])


@router.get("/logs")
async def list_logs(days: int = 7, time_block: Optional[str] = None):
    """Get energy logs for the last N days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    query = "SELECT * FROM energy_logs WHERE logged_at >= ?"
    params = [start_date]
    
    if time_block:
        query += " AND time_block = ?"
        params.append(time_block)
    
    query += " ORDER BY logged_at DESC"
    
    logs = execute_query(query, tuple(params))
    
    return {
        "logs": [dict(l) for l in logs],
        "averages": calculate_averages([dict(l) for l in logs]),
        "count": len(logs)
    }


@router.get("/today")
async def get_today():
    """Get all logs from today with summary."""
    logs = get_today_logs()
    
    return {
        "logs": [dict(l) for l in logs],
        "averages": calculate_averages([dict(l) for l in logs]),
        "count": len(logs),
        "current_block": get_time_block()
    }


@router.get("/patterns")
async def get_patterns():
    """Get AI-analyzed energy patterns."""
    return analyze_patterns()


@router.get("/best-time")
async def best_time(task_type: str = "deep_work"):
    """Get best time for a specific task type."""
    valid_types = ['deep_work', 'meetings', 'creative', 'admin']
    if task_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"task_type must be one of: {valid_types}"
        )
    return get_best_time_for_task(task_type)


@router.get("/stats")
async def get_stats():
    """Get energy statistics."""
    # Today's data
    today_logs = get_today_logs()
    today_avgs = calculate_averages([dict(l) for l in today_logs])
    
    # Week's data
    week_logs = get_recent_logs(7)
    week_avgs = calculate_averages([dict(l) for l in week_logs])
    block_avgs = get_averages_by_time_block([dict(l) for l in week_logs])
    
    # Find peak/low times
    peak_block = None
    low_block = None
    peak_energy = 0
    low_energy = 6
    
    for block, data in block_avgs.items():
        avg = data.get('avg_energy', 3)
        if avg and avg > peak_energy:
            peak_energy = avg
            peak_block = block
        if avg and avg < low_energy:
            low_energy = avg
            low_block = block
    
    return {
        "today": {
            "logs_count": len(today_logs),
            "averages": today_avgs,
            "current_block": get_time_block()
        },
        "week": {
            "logs_count": len(week_logs),
            "averages": week_avgs,
            "by_time_block": block_avgs
        },
        "insights": {
            "peak_time": peak_block,
            "low_time": low_block
        },
        "has_enough_data": len(week_logs) >= 5
    }
