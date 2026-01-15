"""Free time analysis service for calendar integration."""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import execute_query
from .calendar_service import get_preferences


def get_free_blocks(
    date: str,
    min_duration_minutes: Optional[int] = None
) -> List[Dict]:
    """
    Find free time blocks for a given date.
    
    Args:
        date: Date to analyze (YYYY-MM-DD)
        min_duration_minutes: Minimum block duration (uses preference if not set)
        
    Returns:
        List of free time blocks with start, end, duration, and time of day
    """
    prefs = get_preferences()
    
    if min_duration_minutes is None:
        min_duration_minutes = prefs.get('min_free_block_minutes', 30)
    
    working_start = prefs.get('working_hours_start', '09:00')
    working_end = prefs.get('working_hours_end', '17:00')
    working_days = prefs.get('working_days', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
    
    # Parse date and check if it's a working day
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return []
    
    day_name = target_date.strftime('%a')
    if day_name not in working_days:
        # Non-working day - return full day as free
        return [{
            'start_time': f"{date}T00:00:00",
            'end_time': f"{date}T23:59:59",
            'duration_minutes': 1440,
            'time_of_day': 'all_day'
        }]
    
    # Get calendar events for this date
    start_of_day = f"{date}T00:00:00"
    end_of_day = f"{date}T23:59:59"
    
    events = execute_query("""
        SELECT start_time, end_time, all_day FROM calendar_events
        WHERE date(start_time) = ?
        AND status != 'cancelled'
        ORDER BY start_time ASC
    """, (date,))
    
    # Parse working hours
    work_start = datetime.strptime(f"{date}T{working_start}:00", '%Y-%m-%dT%H:%M:%S')
    work_end = datetime.strptime(f"{date}T{working_end}:00", '%Y-%m-%dT%H:%M:%S')
    
    # Build list of busy periods
    busy_periods = []
    for event in events:
        if event['all_day']:
            # All-day event blocks the whole day
            return []
        
        try:
            start = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
            # Remove timezone for comparison
            start = start.replace(tzinfo=None)
            end = end.replace(tzinfo=None)
            busy_periods.append((start, end))
        except:
            continue
    
    # Sort by start time
    busy_periods.sort(key=lambda x: x[0])
    
    # Find gaps between busy periods
    free_blocks = []
    current_time = work_start
    
    for busy_start, busy_end in busy_periods:
        # Only consider events within working hours
        if busy_end <= work_start or busy_start >= work_end:
            continue
        
        # Adjust for events that extend outside working hours
        busy_start = max(busy_start, work_start)
        busy_end = min(busy_end, work_end)
        
        if current_time < busy_start:
            # There's a gap
            duration = (busy_start - current_time).total_seconds() / 60
            if duration >= min_duration_minutes:
                free_blocks.append({
                    'start_time': current_time.isoformat(),
                    'end_time': busy_start.isoformat(),
                    'duration_minutes': int(duration),
                    'time_of_day': _categorize_time_of_day(current_time)
                })
        
        current_time = max(current_time, busy_end)
    
    # Check for free time after last event
    if current_time < work_end:
        duration = (work_end - current_time).total_seconds() / 60
        if duration >= min_duration_minutes:
            free_blocks.append({
                'start_time': current_time.isoformat(),
                'end_time': work_end.isoformat(),
                'duration_minutes': int(duration),
                'time_of_day': _categorize_time_of_day(current_time)
            })
    
    # If no events, whole working day is free
    if not busy_periods:
        duration = (work_end - work_start).total_seconds() / 60
        free_blocks = [{
            'start_time': work_start.isoformat(),
            'end_time': work_end.isoformat(),
            'duration_minutes': int(duration),
            'time_of_day': 'full_workday'
        }]
    
    return free_blocks


def _categorize_time_of_day(dt: datetime) -> str:
    """Categorize time of day for a datetime."""
    hour = dt.hour
    if hour < 12:
        return 'morning'
    elif hour < 17:
        return 'afternoon'
    else:
        return 'evening'


def suggest_focus_time(date: str, duration_minutes: int = 90) -> Optional[Dict]:
    """
    Suggest optimal focus time based on free blocks and energy patterns.
    
    Args:
        date: Date to find focus time
        duration_minutes: Required block duration for focus work
        
    Returns:
        Suggested time block or None if not available
    """
    free_blocks = get_free_blocks(date, min_duration_minutes=duration_minutes)
    
    if not free_blocks:
        return None
    
    # Get user's energy patterns if available
    energy_preference = _get_peak_energy_time()
    
    # Score blocks by preference
    scored_blocks = []
    for block in free_blocks:
        score = block['duration_minutes']  # Longer is better
        
        # Bonus for matching energy preference
        if block['time_of_day'] == energy_preference:
            score *= 1.5
        
        # Slight preference for morning (focused work)
        if block['time_of_day'] == 'morning':
            score *= 1.2
        
        scored_blocks.append((score, block))
    
    # Return highest scored block
    scored_blocks.sort(key=lambda x: x[0], reverse=True)
    
    if scored_blocks:
        best_block = scored_blocks[0][1]
        return {
            **best_block,
            'suggested': True,
            'reason': f"Best {best_block['time_of_day']} block with {best_block['duration_minutes']} minutes available"
        }
    
    return None


def _get_peak_energy_time() -> str:
    """Get user's typical peak energy time from patterns."""
    # Check recent energy logs for patterns
    logs = execute_query("""
        SELECT 
            CASE 
                WHEN time(logged_at) < '12:00' THEN 'morning'
                WHEN time(logged_at) < '17:00' THEN 'afternoon'
                ELSE 'evening'
            END as time_of_day,
            AVG(energy_level) as avg_energy
        FROM energy_logs
        WHERE logged_at >= date('now', '-14 days')
        GROUP BY time_of_day
        ORDER BY avg_energy DESC
        LIMIT 1
    """)
    
    if logs:
        return logs[0]['time_of_day']
    
    return 'morning'  # Default to morning


def check_availability(start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Check if a time slot is available.
    
    Args:
        start_time: Start datetime ISO string
        end_time: End datetime ISO string
        
    Returns:
        Availability status and conflicts if any
    """
    conflicts = execute_query("""
        SELECT id, title, start_time, end_time FROM calendar_events
        WHERE status != 'cancelled'
        AND (
            (start_time <= ? AND end_time > ?)
            OR (start_time < ? AND end_time >= ?)
            OR (start_time >= ? AND end_time <= ?)
        )
    """, (start_time, start_time, end_time, end_time, start_time, end_time))
    
    return {
        'available': len(conflicts) == 0,
        'conflicts': [dict(c) for c in conflicts]
    }


def get_day_summary(date: str) -> Dict[str, Any]:
    """
    Get a summary of the day's schedule.
    
    Args:
        date: Date to summarize (YYYY-MM-DD)
        
    Returns:
        Summary with event count, busy hours, and free blocks
    """
    events = execute_query("""
        SELECT * FROM calendar_events
        WHERE date(start_time) = ?
        AND status != 'cancelled'
        ORDER BY start_time ASC
    """, (date,))
    
    free_blocks = get_free_blocks(date)
    
    # Calculate total busy time
    total_busy_minutes = 0
    for event in events:
        if not event['all_day']:
            try:
                start = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(event['end_time'].replace('Z', '+00:00'))
                total_busy_minutes += (end - start).total_seconds() / 60
            except:
                continue
    
    total_free_minutes = sum(b['duration_minutes'] for b in free_blocks)
    
    return {
        'date': date,
        'event_count': len(events),
        'events': [dict(e) for e in events],
        'busy_hours': round(total_busy_minutes / 60, 1),
        'free_hours': round(total_free_minutes / 60, 1),
        'free_blocks': free_blocks,
        'focus_suggestion': suggest_focus_time(date)
    }
