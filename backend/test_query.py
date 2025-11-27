"""
A simple test script to query the API endpoint or directly use the Qdrant client

Usage:
    python test_query.py

Note: This expects the service to be running at http://127.0.0.1:8000 or Qdrant to be running locally if you modify it.
"""

import requests
import os

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

def main():
    q = "How many apples does Pavan have?"
    r = requests.post(f"{BASE}/query/", json={"question": q})
    print('Status:', r.status_code)
    print('Response JSON:', r.json())

if __name__ == '__main__':
    main()
