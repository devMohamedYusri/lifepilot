"""Proactive suggestion service for generating contextual recommendations."""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import execute_query, execute_write
from services.groq_service import call_groq
from core.prompts import MORNING_PLANNING_PROMPT, TASK_SUGGESTION_PROMPT
from core.json_utils import extract_json_from_response

logger = logging.getLogger(__name__)

# Default preferences
DEFAULT_PREFERENCES = {
    'suggestions_enabled': 'true',
    'quiet_hours_start': '22:00',
    'quiet_hours_end': '07:00',
    'max_per_hour': '3',
    'max_per_day': '15',
    'disabled_types': '[]',
    'min_priority': 'low'
}

# Priority order for filtering
PRIORITY_ORDER = {'high': 3, 'medium': 2, 'low': 1}


def evaluate_context() -> Dict[str, Any]:
    """Evaluate current context for suggestion generation."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    # Item counts
    items = execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN type = 'task' AND status != 'done' THEN 1 ELSE 0 END) as tasks,
            SUM(CASE WHEN type = 'waiting_for' AND status != 'done' THEN 1 ELSE 0 END) as waiting,
            SUM(CASE WHEN due_date < ? AND status != 'done' THEN 1 ELSE 0 END) as overdue
        FROM items
    """, (today,))
    
    item_counts = items[0] if items else {'total': 0, 'tasks': 0, 'waiting': 0, 'overdue': 0}
    
    # Last energy log
    energy = execute_query("""
        SELECT * FROM energy_logs 
        ORDER BY logged_at DESC LIMIT 1
    """)
    last_energy = dict(energy[0]) if energy else None
    hours_since_energy = None
    if last_energy and last_energy.get('logged_at'):
        try:
            log_time = datetime.fromisoformat(last_energy['logged_at'].replace('Z', ''))
            hours_since_energy = (now - log_time).total_seconds() / 3600
        except:
            pass
    
    # Overdue contacts
    overdue_contacts = execute_query("""
        SELECT COUNT(*) as count FROM contacts 
        WHERE is_active = 1 AND next_contact_date <= ?
    """, (today,))
    contact_count = overdue_contacts[0]['count'] if overdue_contacts else 0
    
    # Unread bookmarks
    unread = execute_query("""
        SELECT COUNT(*) as count FROM bookmarks WHERE status = 'unread'
    """)
    unread_count = unread[0]['count'] if unread else 0
    
    # Recent activity (items completed today)
    recent = execute_query("""
        SELECT COUNT(*) as count FROM items 
        WHERE status = 'done' AND date(updated_at) = ?
    """, (today,))
    completed_today = recent[0]['count'] if recent else 0
    
    # Days since last activity
    last_activity = execute_query("""
        SELECT MAX(updated_at) as last FROM items
    """)
    days_inactive = 0
    if last_activity and last_activity[0]['last']:
        try:
            last_time = datetime.fromisoformat(last_activity[0]['last'].replace('Z', ''))
            days_inactive = (now - last_time).days
        except:
            pass
    
    return {
        'current_time': now.isoformat(),
        'hour': now.hour,
        'day_name': now.strftime("%A"),
        'item_counts': dict(item_counts),
        'last_energy': last_energy,
        'hours_since_energy': hours_since_energy,
        'overdue_contacts': contact_count,
        'unread_bookmarks': unread_count,
        'completed_today': completed_today,
        'days_inactive': days_inactive,
        'is_workday': now.weekday() < 5
    }


def get_preferences() -> Dict[str, Any]:
    """Get user suggestion preferences."""
    prefs = execute_query("SELECT key, value FROM suggestion_preferences")
    result = dict(DEFAULT_PREFERENCES)
    
    for pref in prefs:
        result[pref['key']] = pref['value']
    
    # Parse special values
    result['suggestions_enabled'] = result['suggestions_enabled'] == 'true'
    result['max_per_hour'] = int(result['max_per_hour'])
    result['max_per_day'] = int(result['max_per_day'])
    try:
        result['disabled_types'] = json.loads(result['disabled_types'])
    except:
        result['disabled_types'] = []
    
    return result


def update_preferences(updates: Dict[str, Any]) -> None:
    """Update user suggestion preferences."""
    now = datetime.now().isoformat()
    
    for key, value in updates.items():
        # Serialize lists
        if isinstance(value, list):
            value = json.dumps(value)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        else:
            value = str(value)
        
        execute_write("""
            INSERT OR REPLACE INTO suggestion_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))


def check_fatigue_limits(preferences: Dict) -> Dict[str, bool]:
    """Check if suggestion limits have been reached."""
    now = datetime.now()
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    start_of_day = now.replace(hour=0, minute=0, second=0).isoformat()
    
    # Count suggestions shown in last hour
    hourly = execute_query("""
        SELECT COUNT(*) as count FROM suggestions 
        WHERE shown_at >= ? AND status IN ('shown', 'acted', 'dismissed')
    """, (one_hour_ago,))
    hourly_count = hourly[0]['count'] if hourly else 0
    
    # Count suggestions shown today
    daily = execute_query("""
        SELECT COUNT(*) as count FROM suggestions 
        WHERE shown_at >= ? AND status IN ('shown', 'acted', 'dismissed')
    """, (start_of_day,))
    daily_count = daily[0]['count'] if daily else 0
    
    return {
        'hourly_ok': hourly_count < preferences.get('max_per_hour', 3),
        'daily_ok': daily_count < preferences.get('max_per_day', 15),
        'hourly_count': hourly_count,
        'daily_count': daily_count
    }


def is_in_quiet_hours(preferences: Dict) -> bool:
    """Check if current time is within quiet hours."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    start = preferences.get('quiet_hours_start', '22:00')
    end = preferences.get('quiet_hours_end', '07:00')
    
    # Handle overnight quiet hours
    if start > end:
        return current_time >= start or current_time < end
    else:
        return start <= current_time < end


def get_last_suggestion_time(template_type: str) -> Optional[datetime]:
    """Get the last time a suggestion of this type was created."""
    result = execute_query("""
        SELECT MAX(created_at) as last FROM suggestions 
        WHERE template_type = ?
    """, (template_type,))
    
    if result and result[0]['last']:
        try:
            return datetime.fromisoformat(result[0]['last'].replace('Z', ''))
        except:
            pass
    return None


def generate_suggestions(force: bool = False) -> Dict[str, Any]:
    """Generate contextual suggestions based on current state."""
    preferences = get_preferences()
    
    # Check if suggestions are enabled
    if not preferences.get('suggestions_enabled', True) and not force:
        return {'generated': 0, 'reason': 'Suggestions disabled'}
    
    # Check quiet hours
    if is_in_quiet_hours(preferences) and not force:
        return {'generated': 0, 'reason': 'In quiet hours'}
    
    # Check fatigue limits
    limits = check_fatigue_limits(preferences)
    if not limits['hourly_ok'] and not force:
        return {'generated': 0, 'reason': 'Hourly limit reached'}
    if not limits['daily_ok'] and not force:
        return {'generated': 0, 'reason': 'Daily limit reached'}
    
    context = evaluate_context()
    now = datetime.now()
    generated = []
    
    # Get active templates
    templates = execute_query("""
        SELECT * FROM suggestion_templates WHERE is_active = 1
    """)
    
    disabled_types = preferences.get('disabled_types', [])
    min_priority = PRIORITY_ORDER.get(preferences.get('min_priority', 'low'), 1)
    
    for template in templates:
        template_type = template['template_type']
        
        # Skip disabled types
        if template_type in disabled_types:
            continue
        
        # Check priority threshold
        template_priority = PRIORITY_ORDER.get(template['priority'], 2)
        if template_priority < min_priority:
            continue
        
        # Check minimum interval
        min_interval = template['min_interval_hours'] or 24
        last_time = get_last_suggestion_time(template_type)
        if last_time:
            hours_since = (now - last_time).total_seconds() / 3600
            if hours_since < min_interval and not force:
                continue
        
        # Evaluate trigger condition
        if should_trigger(template, context):
            suggestion = create_suggestion(template, context)
            if suggestion:
                generated.append(suggestion)
    
    # Cleanup expired suggestions
    cleanup_expired()
    
    return {
        'generated': len(generated),
        'suggestions': generated
    }


def should_trigger(template: Dict, context: Dict) -> bool:
    """Check if a template should trigger based on context."""
    template_type = template['template_type']
    hour = context['hour']
    
    # Morning planning: 7-9 AM on workdays
    if template_type == 'morning_planning':
        return 7 <= hour <= 9 and context['is_workday']
    
    # End of day review: 5-7 PM
    if template_type == 'end_of_day_review':
        return 17 <= hour <= 19 and context['completed_today'] > 0
    
    # Energy check: 4+ hours since last log during work hours
    if template_type == 'energy_check':
        hours_since = context.get('hours_since_energy')
        return hours_since and hours_since >= 4 and 8 <= hour <= 20
    
    # Overdue nudge: has overdue items
    if template_type == 'overdue_nudge':
        overdue = context['item_counts'].get('overdue', 0)
        return overdue and overdue > 0
    
    # Contact reminder: has overdue contacts
    if template_type == 'contact_reminder':
        return context['overdue_contacts'] > 0
    
    # Reading suggestion: has unread bookmarks and low activity
    if template_type == 'reading_suggestion':
        return context['unread_bookmarks'] > 0 and context['completed_today'] < 3
    
    # Achievement: celebrate when completed 5+ items today
    if template_type == 'achievement':
        return context['completed_today'] >= 5
    
    # Task timing: during work hours
    if template_type == 'task_timing':
        return 9 <= hour <= 17 and context['item_counts'].get('tasks', 0) > 0
    
    return False


def create_suggestion(template: Dict, context: Dict) -> Optional[Dict]:
    """Create a suggestion from a template and context."""
    now = datetime.now()
    
    # Build message from template
    message_template = template['message_template'] or ''
    
    # Replace placeholders
    replacements = {
        'pending_count': str(context['item_counts'].get('total', 0)),
        'overdue_count': str(context['item_counts'].get('overdue', 0)),
        'unread_count': str(context['unread_bookmarks']),
        'completed_today': str(context['completed_today']),
        'streak_days': '3',  # Would need streak calculation
        'task_type': 'focused',
        'suggested_task': 'your top priority'
    }
    
    message = message_template
    for key, value in replacements.items():
        message = message.replace('{' + key + '}', value)
    
    # Determine title and action
    titles = {
        'morning_planning': '🌅 Plan Your Day',
        'end_of_day_review': '🌆 Daily Review',
        'energy_check': '⚡ Energy Check-in',
        'overdue_nudge': '⏰ Overdue Items',
        'contact_reminder': '👋 Stay Connected',
        'reading_suggestion': '📚 Time to Read',
        'achievement': '🏆 Great Progress!',
        'task_timing': '✨ Perfect Time'
    }
    
    deep_links = {
        'morning_planning': '/tasks',
        'end_of_day_review': '/review',
        'energy_check': '/energy',
        'overdue_nudge': '/tasks',
        'contact_reminder': '/people',
        'reading_suggestion': '/bookmarks',
        'achievement': '/patterns',
        'task_timing': '/tasks'
    }
    
    template_type = template['template_type']
    title = titles.get(template_type, 'Suggestion')
    
    # Calculate expiration (suggestions expire after 4 hours)
    expires_at = (now + timedelta(hours=4)).isoformat()
    
    # Insert suggestion
    suggestion_id = execute_write("""
        INSERT INTO suggestions (
            template_id, template_type, title, message, context_data,
            action_type, deep_link, priority, scheduled_for, expires_at, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        template['id'],
        template_type,
        title,
        message,
        json.dumps(context),
        'navigate',
        deep_links.get(template_type, '/'),
        template['priority'],
        now.isoformat(),
        expires_at,
        now.isoformat()
    ))
    
    return {
        'id': suggestion_id,
        'template_type': template_type,
        'title': title,
        'message': message,
        'priority': template['priority'],
        'deep_link': deep_links.get(template_type, '/')
    }


def get_pending_suggestions(limit: int = 5) -> List[Dict]:
    """Get pending suggestions ready to show."""
    now = datetime.now().isoformat()
    
    suggestions = execute_query("""
        SELECT * FROM suggestions 
        WHERE status = 'pending'
        AND scheduled_for <= ?
        AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY 
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            created_at ASC
        LIMIT ?
    """, (now, now, limit))
    
    return [dict(s) for s in suggestions]


def mark_shown(suggestion_id: int) -> None:
    """Mark a suggestion as shown."""
    now = datetime.now().isoformat()
    execute_write("""
        UPDATE suggestions 
        SET status = 'shown', shown_at = ?
        WHERE id = ?
    """, (now, suggestion_id))
    
    # Update stats
    suggestion = execute_query("SELECT template_type FROM suggestions WHERE id = ?", (suggestion_id,))
    if suggestion:
        template_type = suggestion[0]['template_type']
        execute_write("""
            INSERT INTO suggestion_stats (template_type, times_shown, updated_at)
            VALUES (?, 1, ?)
            ON CONFLICT(template_type) DO UPDATE SET 
                times_shown = times_shown + 1,
                updated_at = ?
        """, (template_type, now, now))


def record_response(suggestion_id: int, response_type: str) -> None:
    """Record user response to a suggestion."""
    now = datetime.now()
    
    # Get suggestion details
    suggestion = execute_query("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,))
    if not suggestion:
        return
    
    sug = suggestion[0]
    template_type = sug['template_type']
    
    # Calculate response time if shown
    response_seconds = None
    if sug['shown_at']:
        try:
            shown_time = datetime.fromisoformat(sug['shown_at'].replace('Z', ''))
            response_seconds = (now - shown_time).total_seconds()
        except:
            pass
    
    # Update suggestion status
    status = 'acted' if response_type == 'acted' else 'dismissed'
    execute_write("""
        UPDATE suggestions 
        SET status = ?, response_at = ?, response_type = ?
        WHERE id = ?
    """, (status, now.isoformat(), response_type, suggestion_id))
    
    # Update stats
    if response_type == 'acted':
        execute_write("""
            UPDATE suggestion_stats 
            SET times_acted = times_acted + 1, updated_at = ?
            WHERE template_type = ?
        """, (now.isoformat(), template_type))
    else:
        execute_write("""
            UPDATE suggestion_stats 
            SET times_dismissed = times_dismissed + 1, updated_at = ?
            WHERE template_type = ?
        """, (now.isoformat(), template_type))
    
    # Update effectiveness score
    update_effectiveness(template_type)


def update_effectiveness(template_type: str) -> None:
    """Update effectiveness score for a suggestion type."""
    stats = execute_query("""
        SELECT times_shown, times_acted, times_dismissed 
        FROM suggestion_stats WHERE template_type = ?
    """, (template_type,))
    
    if not stats:
        return
    
    s = stats[0]
    total_responses = (s['times_acted'] or 0) + (s['times_dismissed'] or 0)
    
    if total_responses > 0:
        # Effectiveness = acted / (acted + dismissed) with a smoothing factor
        acted = s['times_acted'] or 0
        effectiveness = (acted + 1) / (total_responses + 2)  # Laplace smoothing
        
        execute_write("""
            UPDATE suggestion_stats 
            SET effectiveness_score = ?
            WHERE template_type = ?
        """, (effectiveness, template_type))


def get_stats() -> List[Dict]:
    """Get suggestion effectiveness statistics."""
    stats = execute_query("""
        SELECT * FROM suggestion_stats ORDER BY effectiveness_score DESC
    """)
    return [dict(s) for s in stats]


def cleanup_expired() -> None:
    """Mark expired suggestions."""
    now = datetime.now().isoformat()
    execute_write("""
        UPDATE suggestions 
        SET status = 'expired'
        WHERE status = 'pending' AND expires_at < ?
    """, (now,))
