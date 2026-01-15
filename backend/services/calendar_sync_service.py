"""Calendar synchronization service."""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import execute_query, execute_write
from .calendar_service import (
    get_connection_with_tokens, 
    get_provider, 
    refresh_connection_tokens,
    update_connection_status
)
from .calendar.calendar_provider import CalendarEvent

logger = logging.getLogger(__name__)


def sync_import(connection_id: int, days_back: int = 7, days_forward: int = 30) -> Dict[str, Any]:
    """Import events from calendar provider."""
    conn = get_connection_with_tokens(connection_id)
    if not conn:
        return {'error': 'Connection not found', 'status': 'failed'}
    
    # Refresh tokens if needed
    if not refresh_connection_tokens(connection_id):
        return {'error': 'Token refresh failed', 'status': 'failed'}
    
    # Re-fetch with new tokens
    conn = get_connection_with_tokens(connection_id)
    
    provider = get_provider(conn['provider'])
    if not provider:
        return {'error': f"Unknown provider: {conn['provider']}", 'status': 'failed'}
    
    # Start sync log
    now = datetime.now()
    log_id = execute_write("""
        INSERT INTO calendar_sync_logs (connection_id, direction, started_at, status)
        VALUES (?, 'import', ?, 'partial')
    """, (connection_id, now.isoformat()))
    
    imported = 0
    updated = 0
    errors = []
    
    try:
        # Fetch events from provider
        start_date = now - timedelta(days=days_back)
        end_date = now + timedelta(days=days_forward)
        
        events = provider.fetch_events(conn['access_token'], start_date, end_date)
        
        for event in events:
            try:
                result = _upsert_event(connection_id, event)
                if result == 'created':
                    imported += 1
                elif result == 'updated':
                    updated += 1
            except Exception as e:
                errors.append(f"Event {event.external_id}: {str(e)}")
        
        status = 'success' if not errors else 'partial'
        
    except Exception as e:
        logger.error(f"Import sync failed: {e}")
        errors.append(str(e))
        status = 'failed'
    
    # Update sync log
    execute_write("""
        UPDATE calendar_sync_logs SET
            completed_at = ?,
            imported_count = ?,
            updated_count = ?,
            errors = ?,
            status = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        imported,
        updated,
        json.dumps(errors) if errors else None,
        status,
        log_id
    ))
    
    # Update connection last sync time
    execute_write("""
        UPDATE calendar_connections SET last_sync_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), connection_id))
    
    return {
        'imported_count': imported,
        'updated_count': updated,
        'errors': errors,
        'status': status
    }


def _upsert_event(connection_id: int, event: CalendarEvent) -> str:
    """Insert or update a calendar event."""
    now = datetime.now().isoformat()
    
    # Check if event exists
    existing = execute_query("""
        SELECT id FROM calendar_events 
        WHERE connection_id = ? AND external_id = ?
    """, (connection_id, event.external_id))
    
    if existing:
        # Update existing
        execute_write("""
            UPDATE calendar_events SET
                title = ?, description = ?, start_time = ?, end_time = ?,
                all_day = ?, location = ?, recurrence_rule = ?, status = ?,
                last_synced_at = ?
            WHERE id = ?
        """, (
            event.title,
            event.description,
            event.start_time.isoformat(),
            event.end_time.isoformat(),
            1 if event.all_day else 0,
            event.location,
            event.recurrence_rule,
            event.status,
            now,
            existing[0]['id']
        ))
        return 'updated'
    else:
        # Insert new
        execute_write("""
            INSERT INTO calendar_events (
                connection_id, external_id, title, description,
                start_time, end_time, all_day, location, recurrence_rule,
                status, is_lifepilot_created, last_synced_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            connection_id,
            event.external_id,
            event.title,
            event.description,
            event.start_time.isoformat(),
            event.end_time.isoformat(),
            1 if event.all_day else 0,
            event.location,
            event.recurrence_rule,
            event.status,
            now,
            now
        ))
        return 'created'


def sync_export(connection_id: int) -> Dict[str, Any]:
    """Export LifePilot items to calendar."""
    conn = get_connection_with_tokens(connection_id)
    if not conn:
        return {'error': 'Connection not found', 'status': 'failed'}
    
    # Refresh tokens if needed
    if not refresh_connection_tokens(connection_id):
        return {'error': 'Token refresh failed', 'status': 'failed'}
    
    # Re-fetch with new tokens
    conn = get_connection_with_tokens(connection_id)
    
    provider = get_provider(conn['provider'])
    if not provider:
        return {'error': f"Unknown provider: {conn['provider']}", 'status': 'failed'}
    
    # Start sync log
    now = datetime.now()
    log_id = execute_write("""
        INSERT INTO calendar_sync_logs (connection_id, direction, started_at, status)
        VALUES (?, 'export', ?, 'partial')
    """, (connection_id, now.isoformat()))
    
    exported = 0
    updated = 0
    errors = []
    
    try:
        # Get items with due dates that haven't been synced
        items = execute_query("""
            SELECT i.*, ce.external_id as calendar_external_id
            FROM items i
            LEFT JOIN calendar_events ce ON ce.linked_item_id = i.id
            WHERE i.due_date IS NOT NULL
            AND i.status != 'done'
            AND i.due_date >= date('now')
        """)
        
        for item in items:
            try:
                # Create calendar event from item
                due_date = datetime.fromisoformat(item['due_date'])
                
                event = CalendarEvent(
                    external_id=item.get('calendar_external_id', ''),
                    title=f"[LifePilot] {item['title']}",
                    start_time=due_date.replace(hour=9, minute=0),
                    end_time=due_date.replace(hour=10, minute=0),
                    description=item.get('details', ''),
                    all_day=False
                )
                
                if item.get('calendar_external_id'):
                    # Update existing calendar event
                    if provider.update_event(conn['access_token'], event):
                        updated += 1
                else:
                    # Create new calendar event
                    external_id = provider.create_event(conn['access_token'], event)
                    
                    # Store link to calendar event
                    execute_write("""
                        INSERT INTO calendar_events (
                            connection_id, external_id, title, start_time, end_time,
                            is_lifepilot_created, linked_item_id, last_synced_at, created_at
                        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """, (
                        connection_id,
                        external_id,
                        event.title,
                        event.start_time.isoformat(),
                        event.end_time.isoformat(),
                        item['id'],
                        now.isoformat(),
                        now.isoformat()
                    ))
                    exported += 1
                    
            except Exception as e:
                errors.append(f"Item {item['id']}: {str(e)}")
        
        status = 'success' if not errors else 'partial'
        
    except Exception as e:
        logger.error(f"Export sync failed: {e}")
        errors.append(str(e))
        status = 'failed'
    
    # Update sync log
    execute_write("""
        UPDATE calendar_sync_logs SET
            completed_at = ?,
            exported_count = ?,
            updated_count = ?,
            errors = ?,
            status = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        exported,
        updated,
        json.dumps(errors) if errors else None,
        status,
        log_id
    ))
    
    return {
        'exported_count': exported,
        'updated_count': updated,
        'errors': errors,
        'status': status
    }


def run_full_sync(connection_id: int) -> Dict[str, Any]:
    """Run bi-directional sync."""
    import_result = sync_import(connection_id)
    export_result = sync_export(connection_id)
    
    # Determine overall status
    statuses = [import_result.get('status'), export_result.get('status')]
    if 'failed' in statuses:
        overall_status = 'failed'
    elif 'partial' in statuses:
        overall_status = 'partial'
    else:
        overall_status = 'success'
    
    return {
        'import': import_result,
        'export': export_result,
        'status': overall_status
    }


def get_events(
    connection_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict]:
    """Get stored calendar events."""
    query = "SELECT * FROM calendar_events WHERE 1=1"
    params = []
    
    if connection_id:
        query += " AND connection_id = ?"
        params.append(connection_id)
    
    if start_date:
        query += " AND start_time >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND end_time <= ?"
        params.append(end_date)
    
    query += " ORDER BY start_time ASC"
    
    events = execute_query(query, tuple(params))
    return [dict(e) for e in events]


def get_sync_logs(connection_id: int, limit: int = 10) -> List[Dict]:
    """Get sync logs for a connection."""
    logs = execute_query("""
        SELECT * FROM calendar_sync_logs 
        WHERE connection_id = ?
        ORDER BY started_at DESC
        LIMIT ?
    """, (connection_id, limit))
    return [dict(l) for l in logs]
