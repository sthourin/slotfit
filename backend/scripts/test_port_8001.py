"""Start server on 8001 and test it"""
import subprocess
import time
import requests
import sys

# Start uvicorn on port 8001 in background
print("Starting uvicorn on port 8001...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"C:\Projects\slotfit\backend"
)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(5)

# Test the endpoint
try:
    r = requests.get('http://localhost:8001/api/v1/exercises/', params={'limit': 5})
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Success! Found {len(data.get('exercises', []))} exercises")
        print(f"Total in database: {data.get('total', 'unknown')}")
    else:
        print(f"Error: {r.text[:200]}")
except Exception as e:
    print(f"Request failed: {e}")

# Kill the server
print("\nStopping test server...")
proc.terminate()
proc.wait()
print("Done.")
