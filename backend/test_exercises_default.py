import requests

try:
    # Test with default include_variants=True
    r = requests.get('http://localhost:8000/api/v1/exercises/', params={'limit': 5})
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'Exercises: {len(data.get("exercises", []))}')
        print(f'Total: {data.get("total", 0)}')
    else:
        try:
            error_data = r.json()
            print(f'Error detail: {error_data.get("detail", "Unknown error")}')
        except:
            print(f'Response text: {r.text[:500]}')
except Exception as e:
    print(f'Request failed: {e}')
