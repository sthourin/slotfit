import requests
import json

try:
    r = requests.get('http://localhost:8000/api/v1/exercises/', params={'limit': 5, 'include_variants': False})
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'Exercises: {len(data.get("exercises", []))}')
        print(f'Total: {data.get("total", 0)}')
        if data.get('exercises'):
            print(f'First exercise: {data["exercises"][0].get("name", "N/A")}')
    else:
        try:
            error_data = r.json()
            print(f'Error detail: {error_data.get("detail", "Unknown error")}')
        except:
            print(f'Response text: {r.text[:500]}')
except Exception as e:
    print(f'Request failed: {e}')
