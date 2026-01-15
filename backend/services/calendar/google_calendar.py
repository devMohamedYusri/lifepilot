"""Google Calendar provider implementation."""
import os
import logging
from typing import List, Optional
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode

from .calendar_provider import CalendarProvider, CalendarEvent, AuthTokens

logger = logging.getLogger(__name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/calendar/callback/google')

# Google API endpoints
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_CALENDAR_API = 'https://www.googleapis.com/calendar/v3'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/userinfo.email'
]


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar API integration."""
    
    @property
    def provider_name(self) -> str:
        return "google"
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    
    def get_auth_url(self, state: str) -> str:
        """Get Google OAuth authorization URL."""
        if not self.is_configured():
            raise ValueError("Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(SCOPES),
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code(self, code: str) -> AuthTokens:
        """Exchange authorization code for tokens."""
        if not self.is_configured():
            raise ValueError("Google OAuth not configured.")
        
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': GOOGLE_REDIRECT_URI
        }
        
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise ValueError(f"Token exchange failed: {response.json().get('error_description', 'Unknown error')}")
        
        tokens = response.json()
        expires_at = None
        if 'expires_in' in tokens:
            expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
        
        return AuthTokens(
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            expires_at=expires_at,
            token_type=tokens.get('token_type', 'Bearer')
        )
    
    def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        """Refresh expired access token."""
        if not self.is_configured():
            raise ValueError("Google OAuth not configured.")
        
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise ValueError("Token refresh failed")
        
        tokens = response.json()
        expires_at = None
        if 'expires_in' in tokens:
            expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
        
        return AuthTokens(
            access_token=tokens['access_token'],
            refresh_token=refresh_token,  # Refresh token doesn't change
            expires_at=expires_at,
            token_type=tokens.get('token_type', 'Bearer')
        )
    
    def fetch_events(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[CalendarEvent]:
        """Fetch calendar events for date range."""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        params = {
            'timeMin': start_date.isoformat() + 'Z',
            'timeMax': end_date.isoformat() + 'Z',
            'singleEvents': 'true',
            'orderBy': 'startTime',
            'maxResults': 250
        }
        
        url = f"{GOOGLE_CALENDAR_API}/calendars/primary/events"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch events: {response.text}")
            return []
        
        events = []
        for item in response.json().get('items', []):
            event = self._parse_google_event(item)
            if event:
                events.append(event)
        
        return events
    
    def _parse_google_event(self, item: dict) -> Optional[CalendarEvent]:
        """Parse a Google Calendar event into our format."""
        try:
            # Handle all-day events
            all_day = 'date' in item.get('start', {})
            
            if all_day:
                start_str = item['start']['date']
                end_str = item['end']['date']
                start_time = datetime.fromisoformat(start_str)
                end_time = datetime.fromisoformat(end_str)
            else:
                start_str = item['start'].get('dateTime', '')
                end_str = item['end'].get('dateTime', '')
                # Handle timezone-aware parsing
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            return CalendarEvent(
                external_id=item['id'],
                title=item.get('summary', 'Untitled'),
                start_time=start_time,
                end_time=end_time,
                description=item.get('description'),
                location=item.get('location'),
                all_day=all_day,
                recurrence_rule=item.get('recurrence', [None])[0] if item.get('recurrence') else None,
                status=item.get('status', 'confirmed')
            )
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None
    
    def create_event(self, access_token: str, event: CalendarEvent) -> str:
        """Create a new calendar event."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        body = self._to_google_event(event)
        url = f"{GOOGLE_CALENDAR_API}/calendars/primary/events"
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code not in (200, 201):
            logger.error(f"Failed to create event: {response.text}")
            raise ValueError(f"Failed to create event: {response.json().get('error', {}).get('message', 'Unknown error')}")
        
        return response.json()['id']
    
    def update_event(self, access_token: str, event: CalendarEvent) -> bool:
        """Update an existing calendar event."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        body = self._to_google_event(event)
        url = f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{event.external_id}"
        
        response = requests.put(url, headers=headers, json=body)
        
        if response.status_code != 200:
            logger.error(f"Failed to update event: {response.text}")
            return False
        
        return True
    
    def delete_event(self, access_token: str, external_id: str) -> bool:
        """Delete a calendar event."""
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{external_id}"
        
        response = requests.delete(url, headers=headers)
        
        # 204 = success, 410 = already deleted
        if response.status_code not in (204, 410):
            logger.error(f"Failed to delete event: {response.text}")
            return False
        
        return True
    
    def _to_google_event(self, event: CalendarEvent) -> dict:
        """Convert our event format to Google Calendar format."""
        body = {
            'summary': event.title,
        }
        
        if event.description:
            body['description'] = event.description
        if event.location:
            body['location'] = event.location
        
        if event.all_day:
            body['start'] = {'date': event.start_time.strftime('%Y-%m-%d')}
            body['end'] = {'date': event.end_time.strftime('%Y-%m-%d')}
        else:
            body['start'] = {'dateTime': event.start_time.isoformat(), 'timeZone': 'UTC'}
            body['end'] = {'dateTime': event.end_time.isoformat(), 'timeZone': 'UTC'}
        
        return body
    
    def get_user_email(self, access_token: str) -> Optional[str]:
        """Get the email of the authenticated user."""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get user info: {response.text}")
            return None
        
        return response.json().get('email')


# Provider instance
google_provider = GoogleCalendarProvider()
