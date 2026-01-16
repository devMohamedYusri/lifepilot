
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(r'c:\test\test1\lifepilot\backend')
sys.path.append(str(backend_path))

try:
    from database import init_db
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")
    
    # Verify tables
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oauth_app_credentials'")
    if cursor.fetchone():
        print("✅ oauth_app_credentials table exists")
    else:
        print("❌ oauth_app_credentials table STILL MISSING")
        
except Exception as e:
    print(f"Error during migration: {str(e)}")
    import traceback
    traceback.print_exc()
