"""Test the endpoint directly with TestClient to see actual error"""
import traceback

try:
    from fastapi.testclient import TestClient
    from app.main import app

    print("Creating TestClient...")
    client = TestClient(app)

    print("Making request to /api/v1/exercises/?limit=5...")
    response = client.get("/api/v1/exercises/?limit=5")

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data.get('exercises', []))} exercises")
    else:
        print(f"Error response: {response.text}")

except Exception as e:
    print(f"\n*** ERROR ***")
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception message: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()
