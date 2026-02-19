
import requests
import json
import time

url = "http://127.0.0.1:8000/api/workflow/analyze"
payload = {"repo_url": "https://github.com/gsd-build/get-shit-done"}

print(f"Sending POST to {url}...")
try:
    start = time.time()
    response = requests.post(url, json=payload, timeout=60)
    end = time.time()
    print(f"Status: {response.status_code}")
    print(f"Took: {end - start:.2f}s")
    if response.ok:
        print("Success:", response.json())
    else:
        print("Error:", response.text)
except Exception as e:
    print(f"Request failed: {e}")
