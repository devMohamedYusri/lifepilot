"""Pattern recognition service for analyzing user behavior and generating insights."""
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import execute_query, execute_write
from services.groq_service import call_groq
from core.prompts import (
    TEMPORAL_PATTERN_PROMPT,
    CORRELATION_ANALYSIS_PROMPT,
    INSIGHT_GENERATION_PROMPT,
)
from core.json_utils import extract_json_from_response

logger = logging.getLogger(__name__)

# Minimum data thresholds for pattern confidence
MIN_TEMPORAL_DAYS = 14
MIN_CORRELATION_PAIRS = 20
MIN_BEHAVIORAL_INSTANCES = 10


def run_full_analysis(
    scope: Optional[List[str]] = None,
    date_range_days: int = 30
) -> Dict[str, Any]:
    """
    Run full pattern analysis across all data types.
    
    Args:
        scope: Optional list of analysis types ['temporal', 'behavioral', 'correlations']
        date_range_days: Number of days to analyze
        
    Returns:
        Analysis result with counts of discovered and updated patterns
    """
    start_time = time.time()
    
    if scope is None:
        scope = ['temporal', 'behavioral', 'correlations']
    
    patterns_discovered = 0
    patterns_updated = 0
    details = {}
    
    start_date = (datetime.now() - timedelta(days=date_range_days)).isoformat()
    
    # Run each analysis type
    if 'temporal' in scope:
        result = analyze_temporal_patterns(start_date)
        patterns_discovered += result.get('discovered', 0)
        patterns_updated += result.get('updated', 0)
        details['temporal'] = result
    
    if 'behavioral' in scope:
        result = analyze_behavioral_patterns(start_date)
        patterns_discovered += result.get('discovered', 0)
        patterns_updated += result.get('updated', 0)
        details['behavioral'] = result
    
    if 'correlations' in scope:
        result = analyze_correlations(start_date)
        patterns_discovered += result.get('discovered', 0)
        patterns_updated += result.get('updated', 0)
        details['correlations'] = result
    
    # Generate insights from patterns
    insights_result = generate_insights()
    insights_generated = insights_result.get('generated', 0)
    
    # Update pattern lifecycle
    update_pattern_lifecycle()
    
    analysis_time_ms = int((time.time() - start_time) * 1000)
    
    return {
        'patterns_discovered': patterns_discovered,
        'patterns_updated': patterns_updated,
        'insights_generated': insights_generated,
        'analysis_time_ms': analysis_time_ms,
        'details': details
    }


def analyze_temporal_patterns(start_date: str) -> Dict[str, Any]:
    """Analyze temporal patterns in task completion and energy levels."""
    
    # Get completed items with timestamps
    completed_items = execute_query("""
        SELECT 
            strftime('%H', updated_at) as hour,
            strftime('%w', updated_at) as day_of_week,
            COUNT(*) as count
        FROM items 
        WHERE status = 'done' AND updated_at >= ?
        GROUP BY hour, day_of_week
    """, (start_date,))
    
    # Get energy logs by time block
    energy_logs = execute_query("""
        SELECT 
            time_block,
            strftime('%w', logged_at) as day_of_week,
            AVG(energy_level) as avg_energy,
            AVG(focus_level) as avg_focus,
            COUNT(*) as count
        FROM energy_logs
        WHERE logged_at >= ?
        GROUP BY time_block, day_of_week
    """, (start_date,))
    
    total_points = sum(r['count'] for r in completed_items) + sum(r['count'] for r in energy_logs)
    
    # Check minimum data threshold
    if total_points < MIN_TEMPORAL_DAYS:
        return {
            'discovered': 0,
            'updated': 0,
            'message': f'Insufficient data. Need at least {MIN_TEMPORAL_DAYS} days of data.'
        }
    
    # Prepare data for AI analysis
    hourly_data = {}
    for row in completed_items:
        hour = row['hour'] or '0'
        hourly_data[hour] = hourly_data.get(hour, 0) + row['count']
    
    daily_data = {}
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    for row in completed_items:
        day = day_names[int(row['day_of_week'] or 0)]
        daily_data[day] = daily_data.get(day, 0) + row['count']
    
    energy_data = []
    for row in energy_logs:
        energy_data.append({
            'time_block': row['time_block'],
            'day': day_names[int(row['day_of_week'] or 0)],
            'avg_energy': round(row['avg_energy'] or 0, 1),
            'avg_focus': round(row['avg_focus'] or 0, 1)
        })
    
    # Call AI for pattern analysis
    prompt = TEMPORAL_PATTERN_PROMPT.format(
        hourly_data=json.dumps(hourly_data),
        daily_data=json.dumps(daily_data),
        energy_data=json.dumps(energy_data[:20]),  # Limit for context
        date_range=f"Last {(datetime.now() - datetime.fromisoformat(start_date.replace('Z', ''))).days} days",
        total_points=total_points
    )
    
    try:
        response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.3)
        result = extract_json_from_response(response, {'patterns': []})
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {'discovered': 0, 'updated': 0, 'error': str(e)}
    
    # Store discovered patterns
    discovered = 0
    updated = 0
    
    for pattern in result.get('patterns', []):
        stored = store_pattern(
            pattern_type=pattern.get('pattern_type', 'temporal'),
            category=pattern.get('category', 'productivity'),
            description=pattern.get('description', ''),
            confidence=pattern.get('confidence', 0.5),
            data_points=pattern.get('data_points', total_points),
            pattern_data=pattern.get('details', {})
        )
        if stored.get('is_new'):
            discovered += 1
        else:
            updated += 1
    
    return {'discovered': discovered, 'updated': updated}


def analyze_behavioral_patterns(start_date: str) -> Dict[str, Any]:
    """Analyze behavioral patterns like task completion rates and procrastination."""
    
    # Get task completion time by type
    completion_times = execute_query("""
        SELECT 
            type,
            AVG(julianday(updated_at) - julianday(created_at)) as avg_days_to_complete,
            COUNT(*) as count
        FROM items 
        WHERE status = 'done' AND updated_at >= ?
        GROUP BY type
    """, (start_date,))
    
    # Get procrastination patterns (items that sit longest)
    stale_items = execute_query("""
        SELECT 
            type,
            priority,
            COUNT(*) as count,
            AVG(julianday('now') - julianday(created_at)) as avg_age_days
        FROM items 
        WHERE status IN ('active', 'inbox') AND created_at >= ?
        GROUP BY type, priority
        HAVING avg_age_days > 7
    """, (start_date,))
    
    total_points = sum(r['count'] for r in completion_times)
    
    if total_points < MIN_BEHAVIORAL_INSTANCES:
        return {
            'discovered': 0,
            'updated': 0,
            'message': f'Insufficient data. Need at least {MIN_BEHAVIORAL_INSTANCES} completed items.'
        }
    
    # Generate patterns locally (simpler analysis)
    patterns = []
    
    # Find fastest and slowest completion types
    if completion_times:
        sorted_times = sorted(completion_times, key=lambda x: x['avg_days_to_complete'] or 999)
        if len(sorted_times) >= 2:
            fastest = sorted_times[0]
            slowest = sorted_times[-1]
            
            if fastest['avg_days_to_complete'] and fastest['count'] >= 5:
                patterns.append({
                    'pattern_type': 'behavioral',
                    'category': 'productivity',
                    'description': f"'{fastest['type']}' items completed fastest, averaging {fastest['avg_days_to_complete']:.1f} days",
                    'confidence': min(0.9, 0.5 + fastest['count'] * 0.02),
                    'data_points': fastest['count'],
                    'details': {'type': fastest['type'], 'avg_days': fastest['avg_days_to_complete']}
                })
    
    # Find procrastination patterns
    for item in stale_items:
        if item['count'] >= 3:
            patterns.append({
                'pattern_type': 'behavioral',
                'category': 'productivity',
                'description': f"Tendency to delay {item['priority']} priority {item['type']} items (avg {item['avg_age_days']:.0f} days old)",
                'confidence': min(0.8, 0.4 + item['count'] * 0.05),
                'data_points': item['count'],
                'details': {'type': item['type'], 'priority': item['priority'], 'avg_age': item['avg_age_days']}
            })
    
    # Store patterns
    discovered = 0
    updated = 0
    
    for pattern in patterns:
        stored = store_pattern(**pattern)
        if stored.get('is_new'):
            discovered += 1
        else:
            updated += 1
    
    return {'discovered': discovered, 'updated': updated}


def analyze_correlations(start_date: str) -> Dict[str, Any]:
    """Analyze correlations between behaviors and outcomes."""
    
    # Get sleep and next-day productivity
    sleep_data = execute_query("""
        SELECT 
            e.sleep_hours,
            (SELECT COUNT(*) FROM items i 
             WHERE i.status = 'done' 
             AND date(i.updated_at) = date(e.logged_at)) as tasks_completed
        FROM energy_logs e
        WHERE e.logged_at >= ? AND e.sleep_hours IS NOT NULL
    """, (start_date,))
    
    # Get exercise and energy correlation
    exercise_data = execute_query("""
        SELECT 
            exercise,
            AVG(energy_level) as avg_energy,
            AVG(focus_level) as avg_focus,
            COUNT(*) as count
        FROM energy_logs
        WHERE logged_at >= ?
        GROUP BY exercise
    """, (start_date,))
    
    # Get context completion rates
    context_data = execute_query("""
        SELECT 
            context,
            COUNT(CASE WHEN status = 'done' THEN 1 END) as completed,
            COUNT(*) as total
        FROM items 
        WHERE created_at >= ?
        GROUP BY context
        HAVING total >= 5
    """, (start_date,))
    
    total_points = len(sleep_data) + len(exercise_data) + len(context_data)
    
    if total_points < MIN_CORRELATION_PAIRS:
        return {
            'discovered': 0,
            'updated': 0,
            'message': f'Insufficient data. Need at least {MIN_CORRELATION_PAIRS} data pairs.'
        }
    
    # Simple correlation analysis
    patterns = []
    
    # Analyze sleep correlation
    if len(sleep_data) >= 10:
        good_sleep = [r for r in sleep_data if (r['sleep_hours'] or 0) >= 7]
        poor_sleep = [r for r in sleep_data if (r['sleep_hours'] or 0) < 7]
        
        if good_sleep and poor_sleep:
            avg_good = sum(r['tasks_completed'] or 0 for r in good_sleep) / len(good_sleep)
            avg_poor = sum(r['tasks_completed'] or 0 for r in poor_sleep) / len(poor_sleep)
            
            if avg_good > avg_poor * 1.2:  # 20% improvement threshold
                patterns.append({
                    'pattern_type': 'correlation',
                    'category': 'energy',
                    'description': f"7+ hours sleep correlates with {((avg_good/avg_poor)-1)*100:.0f}% more tasks completed",
                    'confidence': min(0.85, 0.5 + len(sleep_data) * 0.01),
                    'data_points': len(sleep_data),
                    'details': {'good_sleep_avg': avg_good, 'poor_sleep_avg': avg_poor}
                })
    
    # Analyze exercise correlation
    exercise_on = [r for r in exercise_data if r['exercise']]
    exercise_off = [r for r in exercise_data if not r['exercise']]
    
    if exercise_on and exercise_off:
        on_energy = sum(r['avg_energy'] or 0 for r in exercise_on) / len(exercise_on)
        off_energy = sum(r['avg_energy'] or 0 for r in exercise_off) / len(exercise_off)
        
        if on_energy > off_energy:
            patterns.append({
                'pattern_type': 'correlation',
                'category': 'energy',
                'description': f"Exercise days show {((on_energy/off_energy)-1)*100:.0f}% higher average energy levels",
                'confidence': min(0.8, 0.4 + sum(r['count'] for r in exercise_data) * 0.02),
                'data_points': sum(r['count'] for r in exercise_data),
                'details': {'exercise_energy': on_energy, 'no_exercise_energy': off_energy}
            })
    
    # Analyze context completion rates
    for ctx in context_data:
        if ctx['total'] >= 10:
            rate = (ctx['completed'] or 0) / ctx['total']
            if rate >= 0.7:
                patterns.append({
                    'pattern_type': 'behavioral',
                    'category': 'productivity',
                    'description': f"High completion rate ({rate*100:.0f}%) for '{ctx['context']}' tasks",
                    'confidence': min(0.85, 0.5 + ctx['total'] * 0.02),
                    'data_points': ctx['total'],
                    'details': {'context': ctx['context'], 'completion_rate': rate}
                })
    
    # Store patterns
    discovered = 0
    updated = 0
    
    for pattern in patterns:
        stored = store_pattern(**pattern)
        if stored.get('is_new'):
            discovered += 1
        else:
            updated += 1
    
    return {'discovered': discovered, 'updated': updated}


def store_pattern(
    pattern_type: str,
    category: str,
    description: str,
    confidence: float,
    data_points: int,
    pattern_data: dict = None
) -> Dict[str, Any]:
    """Store or update a pattern in the database."""
    
    # Check if similar pattern exists
    existing = execute_query("""
        SELECT id, confidence, data_points FROM patterns 
        WHERE pattern_type = ? AND category = ? AND description = ?
        LIMIT 1
    """, (pattern_type, category, description))
    
    now = datetime.now().isoformat()
    
    if existing:
        # Update existing pattern
        pattern_id = existing[0]['id']
        old_confidence = existing[0]['confidence'] or 0.5
        old_points = existing[0]['data_points'] or 0
        
        # Weighted average of confidence
        new_confidence = (old_confidence * 0.3 + confidence * 0.7)
        
        execute_write("""
            UPDATE patterns 
            SET confidence = ?, data_points = ?, last_confirmed = ?, pattern_data = ?
            WHERE id = ?
        """, (new_confidence, data_points, now, json.dumps(pattern_data or {}), pattern_id))
        
        return {'id': pattern_id, 'is_new': False}
    else:
        # Create new pattern
        pattern_id = execute_write("""
            INSERT INTO patterns (pattern_type, category, description, confidence, data_points, pattern_data, first_discovered, last_confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pattern_type, category, description, confidence, data_points, json.dumps(pattern_data or {}), now, now))
        
        return {'id': pattern_id, 'is_new': True}


def generate_insights() -> Dict[str, Any]:
    """Generate actionable insights from active patterns."""
    
    # Get active high-confidence patterns
    patterns = execute_query("""
        SELECT * FROM patterns 
        WHERE is_active = 1 AND confidence >= 0.6
        ORDER BY confidence DESC
        LIMIT 10
    """)
    
    if not patterns:
        return {'generated': 0, 'message': 'No high-confidence patterns to generate insights from'}
    
    # Prepare patterns for AI
    patterns_json = []
    for p in patterns:
        patterns_json.append({
            'id': p['id'],
            'type': p['pattern_type'],
            'category': p['category'],
            'description': p['description'],
            'confidence': p['confidence'],
            'data_points': p['data_points']
        })
    
    # Get recent activity summary
    activity = execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM items WHERE status = 'done' AND updated_at >= date('now', '-7 days')) as tasks_completed,
            (SELECT COUNT(*) FROM bookmarks WHERE status = 'completed' AND updated_at >= date('now', '-7 days')) as bookmarks_read,
            (SELECT COUNT(*) FROM decisions WHERE status IN ('decided', 'completed') AND updated_at >= date('now', '-7 days')) as decisions_made
    """)
    
    activity_summary = activity[0] if activity else {'tasks_completed': 0, 'bookmarks_read': 0, 'decisions_made': 0}
    
    # Call AI for insight generation
    prompt = INSIGHT_GENERATION_PROMPT.format(
        patterns_json=json.dumps(patterns_json),
        activity_summary=json.dumps(dict(activity_summary)),
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    try:
        response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
        result = extract_json_from_response(response, {'insights': []})
    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        return {'generated': 0, 'error': str(e)}
    
    # Store insights
    generated = 0
    now = datetime.now().isoformat()
    
    for insight in result.get('insights', []):
        # Check if similar insight already exists
        existing = execute_query("""
            SELECT id FROM insights 
            WHERE title = ? AND status IN ('new', 'seen')
            LIMIT 1
        """, (insight.get('title', ''),))
        
        if not existing:
            execute_write("""
                INSERT INTO insights (pattern_id, insight_type, title, message, priority, suggested_action, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
            """, (
                insight.get('pattern_id'),
                insight.get('insight_type', 'observation'),
                insight.get('title', 'Insight'),
                insight.get('message', ''),
                insight.get('priority', 'medium'),
                insight.get('suggested_action'),
                now
            ))
            generated += 1
    
    return {'generated': generated}


def update_pattern_lifecycle():
    """Update pattern lifecycle - decay old patterns, archive inactive ones."""
    
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    
    # Reduce confidence of patterns not confirmed in 30 days
    execute_write("""
        UPDATE patterns 
        SET confidence = confidence * 0.9
        WHERE last_confirmed < ? AND is_active = 1
    """, (thirty_days_ago,))
    
    # Deactivate very low confidence patterns
    execute_write("""
        UPDATE patterns 
        SET is_active = 0
        WHERE confidence < 0.3 AND is_active = 1
    """)


def get_all_patterns(
    pattern_type: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    active_only: bool = True
) -> List[Dict]:
    """Get all patterns with optional filters."""
    
    query = "SELECT * FROM patterns WHERE 1=1"
    params = []
    
    if active_only:
        query += " AND is_active = 1"
    
    if pattern_type:
        query += " AND pattern_type = ?"
        params.append(pattern_type)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if min_confidence > 0:
        query += " AND confidence >= ?"
        params.append(min_confidence)
    
    query += " ORDER BY confidence DESC, data_points DESC"
    
    results = execute_query(query, tuple(params))
    return [dict(r) for r in results]


def get_pattern_by_id(pattern_id: int) -> Optional[Dict]:
    """Get a specific pattern by ID."""
    results = execute_query("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
    return dict(results[0]) if results else None


def get_active_insights() -> List[Dict]:
    """Get all active (non-dismissed) insights."""
    results = execute_query("""
        SELECT i.*, p.description as pattern_description
        FROM insights i
        LEFT JOIN patterns p ON i.pattern_id = p.id
        WHERE i.status IN ('new', 'seen')
        ORDER BY 
            CASE i.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            i.created_at DESC
    """)
    return [dict(r) for r in results]


def submit_feedback(pattern_id: int, feedback_type: str, comment: Optional[str] = None) -> int:
    """Submit feedback on a pattern and adjust confidence."""
    
    # Store feedback
    feedback_id = execute_write("""
        INSERT INTO pattern_feedback (pattern_id, feedback_type, comment, created_at)
        VALUES (?, ?, ?, ?)
    """, (pattern_id, feedback_type, comment, datetime.now().isoformat()))
    
    # Adjust pattern confidence based on feedback
    confidence_adjustment = {
        'accurate': 0.05,
        'inaccurate': -0.15,
        'helpful': 0.03,
        'not_helpful': -0.05
    }
    
    adjustment = confidence_adjustment.get(feedback_type, 0)
    
    execute_write("""
        UPDATE patterns 
        SET confidence = MAX(0, MIN(1, confidence + ?)),
            user_rating = (SELECT COUNT(*) FROM pattern_feedback WHERE pattern_id = ? AND feedback_type IN ('accurate', 'helpful'))
        WHERE id = ?
    """, (adjustment, pattern_id, pattern_id))
    
    return feedback_id


def get_dashboard_stats() -> Dict[str, Any]:
    """Get aggregate statistics for the pattern dashboard."""
    
    # Total and active patterns
    pattern_counts = execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
            AVG(CASE WHEN is_active = 1 THEN confidence ELSE NULL END) as avg_confidence
        FROM patterns
    """)
    
    # Patterns by type
    by_type = execute_query("""
        SELECT pattern_type, COUNT(*) as count 
        FROM patterns WHERE is_active = 1
        GROUP BY pattern_type
    """)
    
    # Patterns by category
    by_category = execute_query("""
        SELECT category, COUNT(*) as count 
        FROM patterns WHERE is_active = 1
        GROUP BY category
    """)
    
    # Pending insights
    insights_count = execute_query("""
        SELECT COUNT(*) as count FROM insights WHERE status IN ('new', 'seen')
    """)
    
    # Feedback summary
    feedback = execute_query("""
        SELECT feedback_type, COUNT(*) as count 
        FROM pattern_feedback
        GROUP BY feedback_type
    """)
    
    # Last analysis time (newest pattern)
    last_analysis = execute_query("""
        SELECT MAX(last_confirmed) as last FROM patterns
    """)
    
    stats = pattern_counts[0] if pattern_counts else {}
    
    return {
        'total_patterns': stats.get('total', 0) or 0,
        'active_patterns': stats.get('active', 0) or 0,
        'patterns_by_type': {r['pattern_type']: r['count'] for r in by_type},
        'patterns_by_category': {r['category']: r['count'] for r in by_category},
        'avg_confidence': round(stats.get('avg_confidence', 0) or 0, 2),
        'pending_insights': insights_count[0]['count'] if insights_count else 0,
        'feedback_summary': {r['feedback_type']: r['count'] for r in feedback},
        'last_analysis': last_analysis[0]['last'] if last_analysis else None
    }
