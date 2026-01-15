"""CRM service for contact management and AI suggestions."""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .groq_service import call_groq
from database import execute_query


FREQUENCY_DAYS = {
    'weekly': 7,
    'biweekly': 14,
    'monthly': 30,
    'quarterly': 90,
    'yearly': 365,
    'as_needed': 999
}


def calculate_next_contact(last_date: str, frequency: str) -> str:
    """Calculate next contact date based on frequency."""
    if not last_date:
        return datetime.now().strftime("%Y-%m-%d")
    
    try:
        last = datetime.fromisoformat(last_date.split('T')[0])
        days = FREQUENCY_DAYS.get(frequency, 30)
        next_date = last + timedelta(days=days)
        return next_date.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


def get_overdue_contacts() -> List[Dict]:
    """Get contacts that need attention."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    return execute_query("""
        SELECT * FROM contacts 
        WHERE is_active = 1 
        AND (next_contact_date <= ? OR next_contact_date IS NULL)
        ORDER BY relationship_score DESC, next_contact_date ASC
        LIMIT 20
    """, (today,))


def get_upcoming_dates(days: int = 30) -> List[Dict]:
    """Get contacts with birthdays/important dates in the next N days."""
    today = datetime.now()
    results = []
    
    contacts = execute_query("SELECT * FROM contacts WHERE is_active = 1 AND birthday IS NOT NULL")
    
    for contact in contacts:
        birthday = contact.get('birthday')
        if birthday:
            try:
                # Birthday is MM-DD format
                month, day = map(int, birthday.split('-'))
                this_year = today.replace(month=month, day=day)
                
                # If already passed this year, use next year
                if this_year < today:
                    this_year = this_year.replace(year=today.year + 1)
                
                days_until = (this_year - today).days
                if 0 <= days_until <= days:
                    results.append({
                        'contact_id': contact['id'],
                        'name': contact['name'],
                        'event': 'birthday',
                        'date': birthday,
                        'days_until': days_until
                    })
            except:
                pass
    
    return sorted(results, key=lambda x: x['days_until'])


SUGGESTIONS_PROMPT = """Suggest who to reach out to and provide conversation starters. Return ONLY valid JSON.

Contacts needing attention:
{contacts_json}

Recent interactions:
{interactions_json}

Today: {today}

For each contact, provide:
1. Why reach out now
2. Conversation starters based on interests/past topics
3. Suggested interaction type

Return format:
{{
  "suggestions": [
    {{
      "contact_id": 5,
      "contact_name": "John",
      "urgency": "high",
      "reason": "Last contact was 45 days ago",
      "conversation_starters": ["Ask about X", "Share Y"],
      "suggested_type": "call",
      "suggested_message": "Hey! Been a while - want to catch up?"
    }}
  ]
}}"""


def get_contact_suggestions() -> Dict[str, Any]:
    """AI generates contact suggestions."""
    overdue = get_overdue_contacts()
    if not overdue:
        return {"suggestions": [], "message": "All caught up! No contacts need attention right now."}
    
    # Get recent interactions for context
    recent_interactions = execute_query("""
        SELECT i.*, c.name as contact_name 
        FROM interactions i 
        JOIN contacts c ON i.contact_id = c.id 
        ORDER BY i.date DESC LIMIT 20
    """)
    
    # Anonymize for AI
    contacts_for_ai = []
    for c in overdue[:10]:
        contacts_for_ai.append({
            "id": c['id'],
            "name": c['name'][:20] if c.get('name') else "Contact",
            "relationship_type": c.get('relationship_type'),
            "last_contact": c.get('last_contact_date'),
            "desired_frequency": c.get('desired_frequency'),
            "interests": c.get('interests'),
            "conversation_topics": c.get('conversation_topics')
        })
    
    interactions_for_ai = []
    for i in recent_interactions[:10]:
        interactions_for_ai.append({
            "contact_id": i['contact_id'],
            "type": i['type'],
            "date": i['date'],
            "summary": i.get('summary', '')[:100] if i.get('summary') else ""
        })
    
    prompt = SUGGESTIONS_PROMPT.format(
        contacts_json=json.dumps(contacts_for_ai, indent=2),
        interactions_json=json.dumps(interactions_for_ai, indent=2),
        today=datetime.now().strftime("%Y-%m-%d")
    )
    
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.5)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback
        return {
            "suggestions": [
                {
                    "contact_id": c['id'],
                    "contact_name": c['name'],
                    "urgency": "medium",
                    "reason": f"It's been a while since you connected",
                    "conversation_starters": ["Check in on how they're doing"],
                    "suggested_type": "message"
                }
                for c in overdue[:5]
            ]
        }


RELATIONSHIP_PROMPT = """Suggest relationship type and contact frequency. Return ONLY valid JSON.

Contact info:
Name: {name}
How met: {how_met}
Company: {company}
Role: {role}
Notes: {notes}

Suggest appropriate:
1. Relationship type: family, friend, colleague, mentor, mentee, acquaintance, professional, other
2. Desired contact frequency: weekly, biweekly, monthly, quarterly, yearly, as_needed
3. Suggested circles (tags like "work", "college friends", etc.)

Return format:
{{
  "relationship_type": "colleague",
  "desired_frequency": "monthly",
  "circles": ["work", "tech industry"]
}}"""


def suggest_contact_details(contact_data: Dict) -> Dict:
    """AI suggests relationship type and frequency."""
    prompt = RELATIONSHIP_PROMPT.format(
        name=contact_data.get('name', ''),
        how_met=contact_data.get('how_met', ''),
        company=contact_data.get('company', ''),
        role=contact_data.get('role', ''),
        notes=contact_data.get('notes', '')
    )
    
    response = call_groq(prompt, model="llama-3.1-8b-instant", temperature=0.3)
    
    try:
        return json.loads(response)
    except:
        return {
            "relationship_type": "acquaintance",
            "desired_frequency": "monthly",
            "circles": []
        }
