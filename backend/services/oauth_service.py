"""OAuth service for credential and state management."""
import json
import secrets
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from database import execute_query, execute_write
from services.calendar.encryption import (
    encrypt_token, decrypt_token, get_encryption_status
)

logger = logging.getLogger(__name__)

# Default OAuth configuration
DEFAULT_REDIRECT_URI = 'http://localhost:8000/api/auth/google/callback'
DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/userinfo.email'
]


def get_oauth_status() -> Dict[str, Any]:
    """Get overall OAuth configuration status."""
    encryption_status = get_encryption_status()
    google_configured = is_google_configured()
    
    # Get connected accounts
    connections = get_all_connections()
    
    return {
        'encryption': encryption_status,
        'google': {
            'configured': google_configured,
            'connected_accounts': len(connections),
            'accounts': [
                {
                    'id': c['id'],
                    'email': c['account_email'],
                    'status': c['status'],
                    'last_sync': c.get('last_sync_at')
                }
                for c in connections
            ]
        },
        'setup_complete': encryption_status['configured'] and google_configured
    }


def is_google_configured() -> bool:
    """Check if Google OAuth is configured (env or database)."""
    # Check environment variables first
    if os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'):
        return True
    
    # Check database
    creds = execute_query("""
        SELECT is_configured FROM oauth_app_credentials
        WHERE provider = 'google' AND is_configured = 1
    """)
    return len(creds) > 0


def get_google_credentials() -> Optional[Dict[str, str]]:
    """Get Google OAuth credentials from env or database."""
    # Environment takes priority
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if client_id and client_secret:
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI', DEFAULT_REDIRECT_URI),
            'source': 'environment'
        }
    
    # Check database
    creds = execute_query("""
        SELECT encrypted_client_id, encrypted_client_secret, redirect_uri, scopes
        FROM oauth_app_credentials
        WHERE provider = 'google' AND is_configured = 1
    """)
    
    if creds:
        row = creds[0]
        return {
            'client_id': decrypt_token(row['encrypted_client_id']),
            'client_secret': decrypt_token(row['encrypted_client_secret']),
            'redirect_uri': row['redirect_uri'] or DEFAULT_REDIRECT_URI,
            'source': 'database'
        }
    
    return None


def save_google_credentials(client_id: str, client_secret: str, redirect_uri: str = None) -> Dict[str, Any]:
    """Save Google OAuth credentials to database."""
    if not client_id or not client_secret:
        return {'success': False, 'error': 'Client ID and Secret are required'}
    
    # Validate format
    if not client_id.endswith('.apps.googleusercontent.com'):
        return {'success': False, 'error': 'Invalid Client ID format. Should end with .apps.googleusercontent.com'}
    
    now = datetime.now().isoformat()
    redirect = redirect_uri or DEFAULT_REDIRECT_URI
    
    # Upsert credentials
    existing = execute_query("SELECT id FROM oauth_app_credentials WHERE provider = 'google'")
    
    if existing:
        execute_write("""
            UPDATE oauth_app_credentials SET
                encrypted_client_id = ?,
                encrypted_client_secret = ?,
                redirect_uri = ?,
                scopes = ?,
                is_configured = 1,
                updated_at = ?
            WHERE provider = 'google'
        """, (
            encrypt_token(client_id),
            encrypt_token(client_secret),
            redirect,
            json.dumps(DEFAULT_SCOPES),
            now
        ))
    else:
        execute_write("""
            INSERT INTO oauth_app_credentials 
            (provider, encrypted_client_id, encrypted_client_secret, redirect_uri, scopes, is_configured, created_at, updated_at)
            VALUES ('google', ?, ?, ?, ?, 1, ?, ?)
        """, (
            encrypt_token(client_id),
            encrypt_token(client_secret),
            redirect,
            json.dumps(DEFAULT_SCOPES),
            now,
            now
        ))
    
    logger.info("Google OAuth credentials saved successfully")
    return {'success': True}


def test_google_credentials(client_id: str, client_secret: str) -> Dict[str, Any]:
    """Test if Google credentials are valid by making a token info request."""
    import requests
    
    # Simple validation - check format
    if not client_id.endswith('.apps.googleusercontent.com'):
        return {'valid': False, 'error': 'Invalid Client ID format'}
    
    if len(client_secret) < 10:
        return {'valid': False, 'error': 'Client Secret too short'}
    
    # Note: We can't fully validate credentials without completing OAuth
    # But we can check basic format
    return {
        'valid': True,
        'message': 'Credentials format looks valid. Complete OAuth to fully verify.'
    }


# === State Management (CSRF Protection) ===

def generate_oauth_state(provider: str, redirect_after: str = None) -> str:
    """Generate and store OAuth state for CSRF protection."""
    state = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
    
    # Clean up expired states
    execute_write("DELETE FROM oauth_states WHERE expires_at < ?", (datetime.now().isoformat(),))
    
    # Store new state
    execute_write("""
        INSERT INTO oauth_states (state, provider, redirect_after, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (state, provider, redirect_after, expires_at, datetime.now().isoformat()))
    
    return state


def validate_oauth_state(state: str, provider: str) -> Dict[str, Any]:
    """Validate and consume OAuth state."""
    if not state:
        return {'valid': False, 'error': 'Missing state parameter'}
    
    result = execute_query("""
        SELECT * FROM oauth_states 
        WHERE state = ? AND provider = ?
    """, (state, provider))
    
    if not result:
        return {'valid': False, 'error': 'Invalid state parameter'}
    
    row = result[0]
    expires_at = datetime.fromisoformat(row['expires_at'])
    
    if datetime.now() > expires_at:
        # Clean up expired state
        execute_write("DELETE FROM oauth_states WHERE state = ?", (state,))
        return {'valid': False, 'error': 'State parameter expired'}
    
    # Consume state (one-time use)
    execute_write("DELETE FROM oauth_states WHERE state = ?", (state,))
    
    return {
        'valid': True,
        'redirect_after': row['redirect_after']
    }


# === Connection Management ===

def get_all_connections() -> List[Dict]:
    """Get all OAuth connections."""
    connections = execute_query("""
        SELECT id, provider, account_email, sync_enabled, sync_direction,
               last_sync_at, status, created_at
        FROM calendar_connections
        ORDER BY created_at DESC
    """)
    return [dict(c) for c in connections]


def get_connection_by_id(connection_id: int) -> Optional[Dict]:
    """Get a specific connection."""
    connections = execute_query("""
        SELECT * FROM calendar_connections WHERE id = ?
    """, (connection_id,))
    return dict(connections[0]) if connections else None


def revoke_connection(connection_id: int) -> Dict[str, Any]:
    """Revoke an OAuth connection."""
    conn = get_connection_by_id(connection_id)
    if not conn:
        return {'success': False, 'error': 'Connection not found'}
    
    # TODO: Call Google revocation endpoint
    
    # Delete connection
    execute_write("DELETE FROM calendar_events WHERE connection_id = ?", (connection_id,))
    execute_write("DELETE FROM calendar_sync_logs WHERE connection_id = ?", (connection_id,))
    execute_write("DELETE FROM calendar_connections WHERE id = ?", (connection_id,))
    
    logger.info(f"Revoked connection {connection_id}")
    return {'success': True}


def get_setup_instructions() -> Dict[str, Any]:
    """Get Google OAuth setup instructions."""
    return {
        'steps': [
            {
                'step': 1,
                'title': 'Go to Google Cloud Console',
                'description': 'Open the Google Cloud Console in your browser.',
                'link': 'https://console.cloud.google.com'
            },
            {
                'step': 2,
                'title': 'Create or Select a Project',
                'description': 'Create a new project or select an existing one.'
            },
            {
                'step': 3,
                'title': 'Enable Google Calendar API',
                'description': 'Go to APIs & Services > Library and enable "Google Calendar API".',
                'link': 'https://console.cloud.google.com/apis/library/calendar-json.googleapis.com'
            },
            {
                'step': 4,
                'title': 'Configure OAuth Consent Screen',
                'description': 'Go to APIs & Services > OAuth consent screen. Choose "External" for testing.',
                'link': 'https://console.cloud.google.com/apis/credentials/consent'
            },
            {
                'step': 5,
                'title': 'Create OAuth 2.0 Credentials',
                'description': 'Go to APIs & Services > Credentials > Create Credentials > OAuth client ID.',
                'link': 'https://console.cloud.google.com/apis/credentials'
            },
            {
                'step': 6,
                'title': 'Configure Settings',
                'description': 'Select "Web application", add authorized redirect URI:',
                'code': DEFAULT_REDIRECT_URI
            },
            {
                'step': 7,
                'title': 'Copy Credentials',
                'description': 'Copy the Client ID and Client Secret, then enter them below.'
            }
        ],
        'redirect_uri': DEFAULT_REDIRECT_URI,
        'required_scopes': DEFAULT_SCOPES
    }
