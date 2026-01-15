"""Abstract base class for calendar providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalendarEvent:
    """Standardized calendar event format."""
    external_id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: bool = False
    recurrence_rule: Optional[str] = None
    status: str = "confirmed"


@dataclass
class AuthTokens:
    """OAuth tokens from provider."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"


class CalendarProvider(ABC):
    """Abstract base class for calendar provider integrations."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'google')."""
        pass
    
    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """
        Get the OAuth authorization URL.
        
        Args:
            state: CSRF protection state parameter
            
        Returns:
            Authorization URL to redirect user to
        """
        pass
    
    @abstractmethod
    def exchange_code(self, code: str) -> AuthTokens:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            AuthTokens with access and refresh tokens
        """
        pass
    
    @abstractmethod
    def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        """
        Refresh expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New AuthTokens
        """
        pass
    
    @abstractmethod
    def fetch_events(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[CalendarEvent]:
        """
        Fetch calendar events for date range.
        
        Args:
            access_token: Valid access token
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of CalendarEvent objects
        """
        pass
    
    @abstractmethod
    def create_event(self, access_token: str, event: CalendarEvent) -> str:
        """
        Create a new calendar event.
        
        Args:
            access_token: Valid access token
            event: Event to create
            
        Returns:
            External ID of created event
        """
        pass
    
    @abstractmethod
    def update_event(self, access_token: str, event: CalendarEvent) -> bool:
        """
        Update an existing calendar event.
        
        Args:
            access_token: Valid access token
            event: Event with updates (must have external_id)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def delete_event(self, access_token: str, external_id: str) -> bool:
        """
        Delete a calendar event.
        
        Args:
            access_token: Valid access token
            external_id: External ID of event to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_user_email(self, access_token: str) -> Optional[str]:
        """
        Get the email of the authenticated user.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User's email address
        """
        pass
