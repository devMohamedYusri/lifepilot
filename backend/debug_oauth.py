
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(r'c:\test\test1\lifepilot\backend')
sys.path.append(str(backend_path))

try:
    from services.oauth_service import get_oauth_status
    print("Successfully imported oauth_service")
    
    status = get_oauth_status()
    print("Successfully called get_oauth_status")
    print("Status:", status)

except Exception as e:
    print(f"Error occurred: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
