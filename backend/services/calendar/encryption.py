"""Token encryption utilities for OAuth tokens with auto-key generation."""
import base64
import os
import secrets
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Cached encryption key and Fernet instance
_ENCRYPTION_KEY: Optional[str] = None
_fernet_instance: Optional[Fernet] = None


def _find_env_file() -> Path:
    """Find the .env file path."""
    # Check backend directory first
    backend_dir = Path(__file__).parent.parent.parent
    env_path = backend_dir / '.env'
    if env_path.exists():
        return env_path
    
    # Check project root
    project_root = backend_dir.parent
    env_path = project_root / '.env'
    return env_path


def _generate_encryption_key() -> str:
    """Generate a secure random encryption key."""
    return secrets.token_urlsafe(32)[:32]  # 32 characters


def _save_key_to_env(key: str) -> bool:
    """Save encryption key to .env file."""
    env_path = _find_env_file()
    
    try:
        # Read existing content
        existing_content = ""
        if env_path.exists():
            with open(env_path, 'r') as f:
                existing_content = f.read()
        
        # Check if ENCRYPTION_KEY already exists
        if 'ENCRYPTION_KEY=' in existing_content:
            logger.info("ENCRYPTION_KEY already exists in .env file")
            return True
        
        # Append new key
        with open(env_path, 'a') as f:
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write(f'\n# Auto-generated encryption key - keep this safe!\n')
            f.write(f'ENCRYPTION_KEY={key}\n')
        
        logger.info(f"✅ Generated ENCRYPTION_KEY and saved to {env_path}")
        logger.warning("⚠️ Keep this key safe! If you lose it, encrypted data cannot be recovered.")
        return True
    except Exception as e:
        logger.error(f"Failed to save key to .env: {e}")
        return False


def _load_or_generate_key() -> str:
    """Load encryption key from environment or generate and save one."""
    global _ENCRYPTION_KEY
    
    if _ENCRYPTION_KEY:
        return _ENCRYPTION_KEY
    
    # Try to get from environment
    key = os.getenv('ENCRYPTION_KEY')
    
    if not key:
        logger.info("ENCRYPTION_KEY not found. Generating a new one...")
        key = _generate_encryption_key()
        
        # Save to .env file
        if _save_key_to_env(key):
            # Set in current environment for this session
            os.environ['ENCRYPTION_KEY'] = key
        else:
            logger.warning("Could not save key to .env. Using generated key for this session only.")
    
    _ENCRYPTION_KEY = key
    return key


def get_encryption_status() -> dict:
    """Get current encryption status."""
    key = os.getenv('ENCRYPTION_KEY')
    return {
        'configured': bool(key),
        'key_length': len(key) if key else 0,
        'env_file_exists': _find_env_file().exists()
    }


def _get_fernet() -> Optional[Fernet]:
    """Get Fernet instance for encryption/decryption."""
    global _fernet_instance
    
    if _fernet_instance:
        return _fernet_instance
    
    key = _load_or_generate_key()
    
    if not key:
        logger.warning("No encryption key available. Token encryption disabled.")
        return None
    
    try:
        # Derive a proper key from the password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'lifepilot_oauth_salt',
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        _fernet_instance = Fernet(derived_key)
        return _fernet_instance
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        return None


def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    if not token:
        return ""
    
    fernet = _get_fernet()
    if not fernet:
        # Fallback: base64 encoding (not secure, but allows development)
        logger.warning("Using base64 fallback - not secure for production!")
        return f"b64:{base64.b64encode(token.encode()).decode()}"
    
    try:
        encrypted = fernet.encrypt(token.encode()).decode()
        return f"enc:{encrypted}"
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return f"b64:{base64.b64encode(token.encode()).decode()}"


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    if not encrypted_token:
        return ""
    
    # Check for encoding prefix
    if encrypted_token.startswith("enc:"):
        encrypted_token = encrypted_token[4:]
        fernet = _get_fernet()
        if fernet:
            try:
                return fernet.decrypt(encrypted_token.encode()).decode()
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                return ""
        else:
            logger.error("Cannot decrypt - no encryption key available")
            return ""
    elif encrypted_token.startswith("b64:"):
        # Base64 fallback
        try:
            return base64.b64decode(encrypted_token[4:].encode()).decode()
        except:
            return ""
    else:
        # Legacy format - try both methods
        fernet = _get_fernet()
        if fernet:
            try:
                return fernet.decrypt(encrypted_token.encode()).decode()
            except:
                pass
        
        # Try base64 fallback
        try:
            return base64.b64decode(encrypted_token.encode()).decode()
        except:
            return encrypted_token


def validate_encryption_key(key: str) -> dict:
    """Validate an encryption key."""
    if not key:
        return {'valid': False, 'error': 'Key is empty'}
    
    if len(key) < 16:
        return {'valid': False, 'error': 'Key must be at least 16 characters'}
    
    if len(key) > 64:
        return {'valid': False, 'error': 'Key must be at most 64 characters'}
    
    return {'valid': True}
