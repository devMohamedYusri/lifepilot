"""API router for OAuth authentication endpoints."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode

from services.oauth_service import (
    get_oauth_status, is_google_configured, get_google_credentials,
    save_google_credentials, test_google_credentials,
    generate_oauth_state, validate_oauth_state,
    get_all_connections, revoke_connection, get_setup_instructions
)
from services.calendar.encryption import encrypt_token, decrypt_token
from database import execute_query, execute_write

router = APIRouter(prefix="/api/auth", tags=["auth"])


# === Request/Response Models ===

class GoogleCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


class TestCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str


# === Google OAuth URLs ===
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/userinfo.email'
]


# === Status and Setup ===

@router.get("/status")
async def get_auth_status():
    """Get OAuth configuration and connection status."""
    return get_oauth_status()


@router.get("/setup-instructions")
async def get_setup():
    """Get Google OAuth setup instructions."""
    return get_setup_instructions()


# === Credential Management ===

@router.post("/credentials")
async def save_credentials(request: GoogleCredentialsRequest):
    """Save Google OAuth credentials."""
    result = save_google_credentials(
        request.client_id,
        request.client_secret,
        request.redirect_uri
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.post("/test")
async def test_credentials(request: TestCredentialsRequest):
    """Test if Google credentials are valid."""
    return test_google_credentials(request.client_id, request.client_secret)


# === OAuth Flow ===

@router.get("/google")
async def initiate_google_oauth(redirect_after: Optional[str] = None):
    """
    Initiate Google OAuth flow.
    Returns authorization URL to redirect user to.
    """
    if not is_google_configured():
        raise HTTPException(
            status_code=400,
            detail="Google OAuth not configured. Please set up credentials first."
        )
    
    creds = get_google_credentials()
    if not creds:
        raise HTTPException(status_code=500, detail="Failed to retrieve credentials")
    
    # Generate CSRF state
    state = generate_oauth_state('google', redirect_after)
    
    # Build authorization URL
    params = {
        'client_id': creds['client_id'],
        'redirect_uri': creds['redirect_uri'],
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return {
        'auth_url': auth_url,
        'state': state
    }


@router.get("/google/callback")
async def google_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens and creates connection.
    """
    # Handle error from Google
    if error:
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>❌ Authorization Failed</h1>
                <p>Error: {error}</p>
                <p>Please close this window and try again.</p>
                <script>
                    setTimeout(() => {{
                        window.opener && window.opener.postMessage({{ type: 'oauth_error', error: '{error}' }}, '*');
                        window.close();
                    }}, 2000);
                </script>
            </body>
            </html>
        """)
    
    if not code or not state:
        return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head><title>Invalid Request</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>❌ Invalid Request</h1>
                <p>Missing authorization code or state parameter.</p>
            </body>
            </html>
        """)
    
    # Validate state (CSRF protection)
    state_result = validate_oauth_state(state, 'google')
    if not state_result['valid']:
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head><title>Security Error</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>❌ Security Error</h1>
                <p>{state_result['error']}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
        """)
    
    # Get credentials
    creds = get_google_credentials()
    if not creds:
        return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head><title>Configuration Error</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>❌ Configuration Error</h1>
                <p>OAuth credentials not found.</p>
            </body>
            </html>
        """)
    
    # Exchange code for tokens
    try:
        token_response = requests.post(GOOGLE_TOKEN_URL, data={
            'client_id': creds['client_id'],
            'client_secret': creds['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': creds['redirect_uri']
        })
        
        if token_response.status_code != 200:
            error_data = token_response.json()
            error_msg = error_data.get('error_description', error_data.get('error', 'Unknown error'))
            return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head><title>Token Exchange Failed</title></head>
                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                    <h1>❌ Token Exchange Failed</h1>
                    <p>{error_msg}</p>
                </body>
                </html>
            """)
        
        tokens = token_response.json()
        
        # Get user info
        user_response = requests.get(GOOGLE_USERINFO_URL, headers={
            'Authorization': f"Bearer {tokens['access_token']}"
        })
        
        email = 'unknown'
        if user_response.status_code == 200:
            email = user_response.json().get('email', 'unknown')
        
        # Calculate expiration
        expires_at = None
        if 'expires_in' in tokens:
            expires_at = (datetime.now() + timedelta(seconds=tokens['expires_in'])).isoformat()
        
        # Check for existing connection
        existing = execute_query("""
            SELECT id FROM calendar_connections 
            WHERE provider = 'google' AND account_email = ?
        """, (email,))
        
        now = datetime.now().isoformat()
        
        if existing:
            # Update existing connection
            execute_write("""
                UPDATE calendar_connections SET
                    encrypted_access_token = ?,
                    encrypted_refresh_token = ?,
                    token_expires_at = ?,
                    status = 'connected',
                    last_sync_at = NULL
                WHERE id = ?
            """, (
                encrypt_token(tokens['access_token']),
                encrypt_token(tokens.get('refresh_token', '')),
                expires_at,
                existing[0]['id']
            ))
            connection_id = existing[0]['id']
        else:
            # Create new connection
            connection_id = execute_write("""
                INSERT INTO calendar_connections (
                    provider, account_email, encrypted_access_token,
                    encrypted_refresh_token, token_expires_at, status, created_at
                ) VALUES ('google', ?, ?, ?, ?, 'connected', ?)
            """, (
                email,
                encrypt_token(tokens['access_token']),
                encrypt_token(tokens.get('refresh_token', '')),
                expires_at,
                now
            ))
        
        # Return success page that communicates with parent window
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head><title>Connected Successfully</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0;">
                <div style="padding-top: 60px;">
                    <h1 style="font-size: 48px;">✅</h1>
                    <h2>Connected Successfully!</h2>
                    <p style="font-size: 18px; opacity: 0.9;">Account: {email}</p>
                    <p style="opacity: 0.7;">This window will close automatically...</p>
                </div>
                <script>
                    setTimeout(() => {{
                        window.opener && window.opener.postMessage({{ 
                            type: 'oauth_success', 
                            email: '{email}',
                            connection_id: {connection_id}
                        }}, '*');
                        window.close();
                    }}, 1500);
                </script>
            </body>
            </html>
        """)
        
    except Exception as e:
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>❌ Error</h1>
                <p>{str(e)}</p>
            </body>
            </html>
        """)


# === Connection Management ===

@router.get("/connections")
async def list_connections():
    """Get all OAuth connections."""
    return get_all_connections()


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int):
    """Revoke and delete an OAuth connection."""
    result = revoke_connection(connection_id)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error'))
    return result


@router.post("/connections/{connection_id}/refresh")
async def refresh_connection(connection_id: int):
    """Manually refresh tokens for a connection."""
    from services.calendar_service import refresh_connection_tokens
    
    success = refresh_connection_tokens(connection_id)
    if not success:
        raise HTTPException(status_code=400, detail="Token refresh failed")
    
    return {"success": True, "message": "Tokens refreshed successfully"}
