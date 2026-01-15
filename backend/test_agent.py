"""
Test script for Agent API
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/agent"

def test_api():
    print("Testing Agent API...")
    
    # 1. Get Status
    print("\n1. Getting Agent Status...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")
        return
    
    # 2. Start Chat
    print("\n2. Sending Chat Message...")
    chat_payload = {
        "message": "Hello, I need help planning my day."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=chat_payload)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 200
        
        session_id = data['session_id']
        print(f"Session ID: {session_id}")
    except Exception as e:
        print(f"Failed: {e}")
        return
        
    # 3. List Conversations
    print("\n3. Listing Conversations...")
    try:
        response = requests.get(f"{BASE_URL}/conversations")
        print(f"Status Code: {response.status_code}")
        print(f"Count: {len(response.json())}")
        assert response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")
    
    # 4. Get Specific Conversation
    print("\n4. Getting Conversation Details...")
    try:
        response = requests.get(f"{BASE_URL}/conversations/{session_id}")
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Message Count: {data['message_count']}")
        assert response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")

    # 5. Get Settings
    print("\n5. Getting Settings...")
    try:
        response = requests.get(f"{BASE_URL}/settings")
        print(f"Status Code: {response.status_code}")
        print(f"Settings: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_api()
