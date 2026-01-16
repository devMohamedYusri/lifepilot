"""
Production Verification Script
Tests all critical API endpoints and services
"""
import requests
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, expected_status=200, data=None):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PATCH":
            response = requests.patch(url, json=data)
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - OK ({response.status_code})")
            return True
        else:
            print(f"❌ {method} {endpoint} - FAILED (got {response.status_code}, expected {expected_status})")
            return False
    except Exception as e:
        print(f"❌ {method} {endpoint} - ERROR: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("LifePilot Production Verification")
    print("=" * 60)
    print(f"Testing backend at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Core endpoints
    print("🔍 Testing Core Endpoints...")
    results.append(test_endpoint("GET", "/"))
    results.append(test_endpoint("GET", "/api/health"))
    print()
    
    # Items API
    print("📋 Testing Items API...")
    results.append(test_endpoint("GET", "/api/items"))
    results.append(test_endpoint("GET", "/api/items/needs-followup"))
    print()
    
    # Focus API
    print("🎯 Testing Focus API...")
    results.append(test_endpoint("GET", "/api/focus/today"))
    print()
    
    # Bookmarks API
    print("📚 Testing Bookmarks API...")
    results.append(test_endpoint("GET", "/api/bookmarks"))
    print()
    
    # Decisions API
    print("🤔 Testing Decisions API...")
    results.append(test_endpoint("GET", "/api/decisions"))
    print()
    
    # Reviews API
    print("📊 Testing Reviews API...")
    results.append(test_endpoint("GET", "/api/reviews"))
    results.append(test_endpoint("GET", "/api/reviews/current"))
    print()
    
    # Contacts API
    print("👥 Testing Contacts API...")
    results.append(test_endpoint("GET", "/api/contacts"))
    print()
    
    # Energy API
    print("⚡ Testing Energy API...")
    results.append(test_endpoint("GET", "/api/energy/logs"))
    print()
    
    # Notifications API
    print("🔔 Testing Notifications API...")
    results.append(test_endpoint("GET", "/api/notifications/pending"))
    results.append(test_endpoint("GET", "/api/notifications/count"))
    print()
    
    # Patterns API
    print("📈 Testing Patterns API...")
    results.append(test_endpoint("GET", "/api/patterns/insights"))
    print()
    
    # Suggestions API
    print("💡 Testing Suggestions API...")
    results.append(test_endpoint("GET", "/api/suggestions"))
    print()
    
    # Calendar API
    print("📅 Testing Calendar API...")
    results.append(test_endpoint("GET", "/api/calendar/connections"))
    results.append(test_endpoint("GET", "/api/calendar/preferences"))
    print()
    
    # Push API
    print("📲 Testing Push API...")
    results.append(test_endpoint("GET", "/api/push/vapid-key", expected_status=503))  # Expected to fail without VAPID keys
    results.append(test_endpoint("GET", "/api/push/status"))
    print()
    
    # Scheduler API
    print("⏰ Testing Scheduler API...")
    results.append(test_endpoint("GET", "/api/scheduler/tasks"))
    print()
    
    # Search API
    print("🔍 Testing Search API...")
    results.append(test_endpoint("POST", "/api/search", data={"query": "test"}))
    results.append(test_endpoint("GET", "/api/search/suggestions"))
    print()
    
    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"Results: {passed}/{total} tests passed ({percentage:.1f}%)")
    
    if passed == total:
        print("✅ All tests passed! Backend is production ready.")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} tests failed. Review errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
