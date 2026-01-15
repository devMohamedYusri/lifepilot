"""Calendar connection and management service."""
import json
import logging
import secrets
from typing import Dict, Any, List, Optional
from datetime import datetime
from database import execute_query, execute_write
from .calendar.encryption import encrypt_token, decrypt_token
from .calendar.google_calendar import google_provider
from .calendar.calendar_provider import CalendarProvider, AuthTokens

logger = logging.getLogger(__name__)

# Provider registry
PROVIDERS: Dict[str, CalendarProvider] = {
    'google': google_provider
}

# Store OAuth states temporarily (in production, use Redis or database)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def get_provider(provider_name: str) -> Optional[CalendarProvider]:
    """Get a calendar provider by name."""
    return PROVIDERS.get(provider_name)


def generate_oauth_state() -> str:
    """Generate a secure OAuth state parameter."""
    return secrets.token_urlsafe(32)


def store_oauth_state(state: str, data: Dict[str, Any]) -> None:
    """Store OAuth state for verification."""
    _oauth_states[state] = {
        **data,
        'created_at': datetime.now().isoformat()
    }


def verify_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """Verify and consume OAuth state."""
    return _oauth_states.pop(state, None)


def get_auth_url(provider_name: str) -> Dict[str, str]:
    """Get OAuth authorization URL for a provider."""
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    state = generate_oauth_state()
    store_oauth_state(state, {'provider': provider_name})
    
    auth_url = provider.get_auth_url(state)
    return {'auth_url': auth_url, 'state': state}


def complete_oauth(provider_name: str, code: str, state: str) -> Dict[str, Any]:
    """Complete OAuth flow and create connection."""
    # Verify state
    state_data = verify_oauth_state(state)
    if not state_data or state_data.get('provider') != provider_name:
        raise ValueError("Invalid or expired OAuth state")
    
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    # Exchange code for tokens
    tokens = provider.exchange_code(code)
    
    # Get user email
    email = provider.get_user_email(tokens.access_token)
    
    # Check if connection already exists
    existing = execute_query("""
        SELECT id FROM calendar_connections 
        WHERE provider = ? AND account_email = ?
    """, (provider_name, email))
    
    if existing:
        # Update existing connection
        connection_id = existing[0]['id']
        execute_write("""
            UPDATE calendar_connections SET
                encrypted_access_token = ?,
                encrypted_refresh_token = ?,
                token_expires_at = ?,
                status = 'connected',
                last_sync_at = NULL
            WHERE id = ?
        """, (
            encrypt_token(tokens.access_token),
            encrypt_token(tokens.refresh_token) if tokens.refresh_token else None,
            tokens.expires_at.isoformat() if tokens.expires_at else None,
            connection_id
        ))
    else:
        # Create new connection
        connection_id = execute_write("""
            INSERT INTO calendar_connections (
                provider, account_email, encrypted_access_token, 
                encrypted_refresh_token, token_expires_at, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'connected', ?)
        """, (
            provider_name,
            email,
            encrypt_token(tokens.access_token),
            encrypt_token(tokens.refresh_token) if tokens.refresh_token else None,
            tokens.expires_at.isoformat() if tokens.expires_at else None,
            datetime.now().isoformat()
        ))
    
    return {
        'connection_id': connection_id,
        'email': email,
        'provider': provider_name
    }


def get_connections() -> List[Dict]:
    """Get all calendar connections."""
    connections = execute_query("""
        SELECT id, provider, account_email, sync_enabled, sync_direction,
               last_sync_at, status, created_at
        FROM calendar_connections
        ORDER BY created_at DESC
    """)
    return [dict(c) for c in connections]


def get_connection(connection_id: int) -> Optional[Dict]:
    """Get a specific connection by ID."""
    connections = execute_query("""
        SELECT * FROM calendar_connections WHERE id = ?
    """, (connection_id,))
    return dict(connections[0]) if connections else None


def get_connection_with_tokens(connection_id: int) -> Optional[Dict]:
    """Get connection with decrypted tokens."""
    conn = get_connection(connection_id)
    if not conn:
        return None
    
    conn['access_token'] = decrypt_token(conn.get('encrypted_access_token', ''))
    conn['refresh_token'] = decrypt_token(conn.get('encrypted_refresh_token', ''))
    return conn


def delete_connection(connection_id: int) -> bool:
    """Delete a calendar connection and its data."""
    # Delete related events and logs (CASCADE should handle this)
    execute_write("DELETE FROM calendar_events WHERE connection_id = ?", (connection_id,))
    execute_write("DELETE FROM calendar_sync_logs WHERE connection_id = ?", (connection_id,))
    execute_write("DELETE FROM calendar_connections WHERE id = ?", (connection_id,))
    return True


def update_connection_status(connection_id: int, status: str) -> None:
    """Update connection status."""
    execute_write("""
        UPDATE calendar_connections SET status = ? WHERE id = ?
    """, (status, connection_id))


def refresh_connection_tokens(connection_id: int) -> bool:
    """Refresh tokens for a connection if expired."""
    conn = get_connection_with_tokens(connection_id)
    if not conn:
        return False
    
    # Check if tokens need refresh
    expires_at = conn.get('token_expires_at')
    if expires_at:
        try:
            exp_time = datetime.fromisoformat(expires_at.replace('Z', ''))
            if exp_time > datetime.now():
                return True  # Token still valid
        except:
            pass
    
    # Refresh tokens
    provider = get_provider(conn['provider'])
    if not provider:
        return False
    
    try:
        new_tokens = provider.refresh_tokens(conn['refresh_token'])
        
        execute_write("""
            UPDATE calendar_connections SET
                encrypted_access_token = ?,
                token_expires_at = ?,
                status = 'connected'
            WHERE id = ?
        """, (
            encrypt_token(new_tokens.access_token),
            new_tokens.expires_at.isoformat() if new_tokens.expires_at else None,
            connection_id
        ))
        return True
    except Exception as e:
        logger.error(f"Token refresh failed for connection {connection_id}: {e}")
        update_connection_status(connection_id, 'expired')
        return False


def get_preferences() -> Dict[str, Any]:
    """Get calendar preferences."""
    prefs = execute_query("SELECT key, value FROM calendar_preferences")
    result = {}
    
    for pref in prefs:
        key = pref['key']
        value = pref['value']
        
        # Parse JSON values
        if key == 'working_days':
            try:
                value = json.loads(value)
            except:
                value = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        elif value in ('true', 'false'):
            value = value == 'true'
        elif value.isdigit():
            value = int(value)
        
        result[key] = value
    
    return result


def update_preferences(updates: Dict[str, Any]) -> None:
    """Update calendar preferences."""
    now = datetime.now().isoformat()
    
    for key, value in updates.items():
        if isinstance(value, list):
            value = json.dumps(value)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        else:
            value = str(value)
        
        execute_write("""
            INSERT OR REPLACE INTO calendar_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))
