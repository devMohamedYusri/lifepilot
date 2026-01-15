"""Contacts router for Personal CRM."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import datetime
import json

from database import execute_query, execute_write
from services.crm_service import (
    calculate_next_contact, get_overdue_contacts, get_upcoming_dates,
    get_contact_suggestions, suggest_contact_details
)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.post("")
async def create_contact(contact: dict):
    """Create a new contact with AI suggestions."""
    name = contact.get('name')
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    # Get AI suggestions for relationship type and frequency
    suggestions = suggest_contact_details(contact)
    
    # Use suggestions if not provided
    relationship_type = contact.get('relationship_type') or suggestions.get('relationship_type', 'acquaintance')
    desired_frequency = contact.get('desired_frequency') or suggestions.get('desired_frequency', 'monthly')
    circles = contact.get('circles') or suggestions.get('circles', [])
    
    query = """
        INSERT INTO contacts (
            name, nickname, email, phone, photo_url,
            relationship_type, circles, company, role,
            how_met, met_date, introduced_by,
            birthday, anniversary, important_dates,
            desired_frequency, last_contact_date, next_contact_date, relationship_score,
            interests, conversation_topics, notes,
            is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    """
    
    now = datetime.now().isoformat()
    last_contact = contact.get('last_contact_date')
    next_contact = calculate_next_contact(last_contact, desired_frequency) if last_contact else now.split('T')[0]
    
    params = (
        name,
        contact.get('nickname'),
        contact.get('email'),
        contact.get('phone'),
        contact.get('photo_url'),
        relationship_type,
        json.dumps(circles) if isinstance(circles, list) else circles,
        contact.get('company'),
        contact.get('role'),
        contact.get('how_met'),
        contact.get('met_date'),
        contact.get('introduced_by'),
        contact.get('birthday'),
        contact.get('anniversary'),
        json.dumps(contact.get('important_dates', [])),
        desired_frequency,
        last_contact,
        next_contact,
        contact.get('relationship_score', 3),
        json.dumps(contact.get('interests', [])),
        contact.get('conversation_topics'),
        contact.get('notes'),
        now, now
    )
    
    contact_id = execute_write(query, params)
    
    result = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    return {**dict(result[0]), "ai_suggestions": suggestions}


@router.get("")
async def list_contacts(
    relationship_type: Optional[str] = None,
    circle: Optional[str] = None,
    needs_contact: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "name"
):
    """List contacts with filters."""
    query = "SELECT * FROM contacts WHERE is_active = 1"
    params = []
    
    if relationship_type:
        query += " AND relationship_type = ?"
        params.append(relationship_type)
    
    if circle:
        query += " AND circles LIKE ?"
        params.append(f'%{circle}%')
    
    if needs_contact:
        today = datetime.now().strftime("%Y-%m-%d")
        query += " AND (next_contact_date <= ? OR next_contact_date IS NULL)"
        params.append(today)
    
    if search:
        query += " AND (name LIKE ? OR company LIKE ? OR notes LIKE ? OR email LIKE ?)"
        search_pattern = f'%{search}%'
        params.extend([search_pattern] * 4)
    
    # Sorting
    sort_map = {
        'name': 'name ASC',
        'last_contact': 'last_contact_date DESC',
        'relationship_score': 'relationship_score DESC',
        'next_contact': 'next_contact_date ASC'
    }
    query += f" ORDER BY {sort_map.get(sort, 'name ASC')}"
    
    contacts = execute_query(query, tuple(params))
    
    # Add last interaction preview
    result = []
    for c in contacts:
        contact = dict(c)
        # Parse JSON fields
        try:
            contact['circles'] = json.loads(contact.get('circles') or '[]')
            contact['interests'] = json.loads(contact.get('interests') or '[]')
        except:
            pass
        
        # Get last interaction
        last_interaction = execute_query(
            "SELECT * FROM interactions WHERE contact_id = ? ORDER BY date DESC LIMIT 1",
            (contact['id'],)
        )
        if last_interaction:
            contact['last_interaction'] = dict(last_interaction[0])
        
        result.append(contact)
    
    return result


@router.get("/needs-attention")
async def get_needs_attention():
    """Get contacts needing outreach."""
    overdue = get_overdue_contacts()
    upcoming = get_upcoming_dates(30)
    
    return {
        "overdue_contacts": [dict(c) for c in overdue],
        "upcoming_dates": upcoming,
        "total_needing_attention": len(overdue)
    }


@router.get("/suggestions")
async def get_suggestions():
    """Get AI contact suggestions."""
    return get_contact_suggestions()


@router.get("/upcoming-dates")
async def upcoming_dates(days: int = 30):
    """Get upcoming birthdays and important dates."""
    return get_upcoming_dates(days)


@router.get("/stats")
async def get_stats():
    """Get CRM statistics."""
    # Total by type
    type_counts = execute_query("""
        SELECT relationship_type, COUNT(*) as count 
        FROM contacts WHERE is_active = 1 
        GROUP BY relationship_type
    """)
    
    # Interactions this week
    week_ago = (datetime.now() - __import__('datetime').timedelta(days=7)).strftime("%Y-%m-%d")
    week_interactions = execute_query(
        "SELECT COUNT(*) as count FROM interactions WHERE date >= ?",
        (week_ago,)
    )
    
    # Most contacted
    most_contacted = execute_query("""
        SELECT c.id, c.name, COUNT(i.id) as interaction_count
        FROM contacts c
        LEFT JOIN interactions i ON c.id = i.contact_id
        WHERE c.is_active = 1
        GROUP BY c.id
        ORDER BY interaction_count DESC
        LIMIT 5
    """)
    
    # Neglected (no contact in 2x frequency)
    neglected = execute_query("""
        SELECT COUNT(*) as count FROM contacts 
        WHERE is_active = 1 
        AND next_contact_date < date('now', '-30 days')
    """)
    
    return {
        "total_contacts": sum(t['count'] for t in type_counts),
        "by_type": {t['relationship_type']: t['count'] for t in type_counts},
        "interactions_this_week": week_interactions[0]['count'] if week_interactions else 0,
        "most_contacted": [dict(m) for m in most_contacted],
        "neglected_count": neglected[0]['count'] if neglected else 0
    }


@router.get("/{contact_id}")
async def get_contact(contact_id: int):
    """Get contact with recent interactions."""
    contact = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    result = dict(contact[0])
    
    # Parse JSON fields
    try:
        result['circles'] = json.loads(result.get('circles') or '[]')
        result['interests'] = json.loads(result.get('interests') or '[]')
        result['important_dates'] = json.loads(result.get('important_dates') or '[]')
    except:
        pass
    
    # Get interactions
    interactions = execute_query(
        "SELECT * FROM interactions WHERE contact_id = ? ORDER BY date DESC LIMIT 20",
        (contact_id,)
    )
    result['interactions'] = []
    for i in interactions:
        interaction = dict(i)
        try:
            interaction['highlights'] = json.loads(interaction.get('highlights') or '[]')
            interaction['follow_ups'] = json.loads(interaction.get('follow_ups') or '[]')
        except:
            pass
        result['interactions'].append(interaction)
    
    return result


@router.patch("/{contact_id}")
async def update_contact(contact_id: int, updates: dict):
    """Update contact fields."""
    existing = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    allowed_fields = [
        'name', 'nickname', 'email', 'phone', 'photo_url',
        'relationship_type', 'circles', 'company', 'role',
        'how_met', 'met_date', 'introduced_by',
        'birthday', 'anniversary', 'important_dates',
        'desired_frequency', 'last_contact_date', 'relationship_score',
        'interests', 'conversation_topics', 'notes', 'is_active'
    ]
    
    set_clauses = []
    params = []
    
    for field in allowed_fields:
        if field in updates:
            value = updates[field]
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            set_clauses.append(f"{field} = ?")
            params.append(value)
    
    if not set_clauses:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Auto-calculate next_contact_date if last_contact_date updated
    if 'last_contact_date' in updates:
        frequency = updates.get('desired_frequency') or existing[0]['desired_frequency']
        next_contact = calculate_next_contact(updates['last_contact_date'], frequency)
        set_clauses.append("next_contact_date = ?")
        params.append(next_contact)
    
    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(contact_id)
    
    query = f"UPDATE contacts SET {', '.join(set_clauses)} WHERE id = ?"
    execute_write(query, tuple(params))
    
    result = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    return dict(result[0])


@router.delete("/{contact_id}")
async def delete_contact(contact_id: int):
    """Soft delete contact."""
    existing = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    execute_write(
        "UPDATE contacts SET is_active = 0, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), contact_id)
    )
    
    return {"message": "Contact deleted", "id": contact_id}


@router.post("/{contact_id}/interactions")
async def log_interaction(contact_id: int, interaction: dict):
    """Log a new interaction with a contact."""
    existing = execute_query("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    interaction_type = interaction.get('type')
    if not interaction_type:
        raise HTTPException(status_code=400, detail="Interaction type is required")
    
    date = interaction.get('date') or datetime.now().strftime("%Y-%m-%d")
    
    query = """
        INSERT INTO interactions (
            contact_id, type, date, duration_minutes, location,
            summary, highlights, follow_ups, mood, linked_item_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        contact_id,
        interaction_type,
        date,
        interaction.get('duration_minutes'),
        interaction.get('location'),
        interaction.get('summary'),
        json.dumps(interaction.get('highlights', [])),
        json.dumps(interaction.get('follow_ups', [])),
        interaction.get('mood'),
        interaction.get('linked_item_id'),
        datetime.now().isoformat()
    )
    
    interaction_id = execute_write(query, params)
    
    # Update contact's last_contact_date and next_contact_date
    contact = existing[0]
    frequency = contact['desired_frequency'] or 'monthly'
    next_contact = calculate_next_contact(date, frequency)
    
    execute_write(
        "UPDATE contacts SET last_contact_date = ?, next_contact_date = ?, updated_at = ? WHERE id = ?",
        (date, next_contact, datetime.now().isoformat(), contact_id)
    )
    
    result = execute_query("SELECT * FROM interactions WHERE id = ?", (interaction_id,))
    return dict(result[0])


@router.get("/{contact_id}/interactions")
async def get_interactions(contact_id: int, limit: int = 50):
    """Get all interactions for a contact."""
    interactions = execute_query(
        "SELECT * FROM interactions WHERE contact_id = ? ORDER BY date DESC LIMIT ?",
        (contact_id, limit)
    )
    
    result = []
    for i in interactions:
        interaction = dict(i)
        try:
            interaction['highlights'] = json.loads(interaction.get('highlights') or '[]')
            interaction['follow_ups'] = json.loads(interaction.get('follow_ups') or '[]')
        except:
            pass
        result.append(interaction)
    
    return result
