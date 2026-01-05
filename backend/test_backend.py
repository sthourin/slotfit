"""
Simple backend test script
Run this after starting the server to test endpoints
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"


def test_health_check():
    """Test health check endpoint"""
    print("=" * 50)
    print("Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_list_exercises():
    """Test listing exercises"""
    print("\n" + "=" * 50)
    print("Testing List Exercises...")
    try:
        response = requests.get(f"{API_URL}/exercises/", params={"limit": 5})
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total: {data.get('total', 0)}")
        print(f"Returned: {len(data.get('exercises', []))}")
        if data.get('exercises'):
            print(f"First exercise: {data['exercises'][0]['name']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_get_exercise():
    """Test getting single exercise"""
    print("\n" + "=" * 50)
    print("Testing Get Exercise...")
    try:
        response = requests.get(f"{API_URL}/exercises/1")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Exercise: {data.get('name')}")
            print(f"Difficulty: {data.get('difficulty')}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_search_exercises():
    """Test searching exercises"""
    print("\n" + "=" * 50)
    print("Testing Search Exercises...")
    try:
        response = requests.get(f"{API_URL}/exercises/", params={"search": "push", "limit": 3})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('exercises', []))} exercises matching 'push'")
            for ex in data.get('exercises', [])[:3]:
                print(f"  - {ex['name']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_recommendations():
    """Test recommendations"""
    print("\n" + "=" * 50)
    print("Testing Recommendations...")
    try:
        # Use muscle group IDs 1, 2 and equipment ID 1 (adjust based on your data)
        response = requests.get(
            f"{API_URL}/recommendations/",
            params={
                "muscle_group_ids": [1, 2],
                "available_equipment_ids": [1],
                "limit": 3
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total candidates: {data.get('total_candidates', 0)}")
            print(f"Recommendations: {len(data.get('recommendations', []))}")
            for rec in data.get('recommendations', [])[:3]:
                print(f"  - {rec['exercise_name']} (score: {rec['priority_score']:.2f})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests"""
    print("SlotFit Backend Test Suite")
    print("=" * 50)
    print("Make sure the server is running: uvicorn app.main:app --reload")
    print()
    
    results = []
    results.append(("Health Check", test_health_check()))
    results.append(("List Exercises", test_list_exercises()))
    results.append(("Get Exercise", test_get_exercise()))
    results.append(("Search Exercises", test_search_exercises()))
    results.append(("Recommendations", test_recommendations()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {passed_count}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
