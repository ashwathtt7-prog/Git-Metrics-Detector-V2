
import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/workflow"
REPO_URL = "https://github.com/gsd-build/get-shit-done"

def test_analyze_flow():
    print(f"Starting E2E Analysis Test for {REPO_URL}...")
    
    # 1. Start Analysis
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/analyze", json={"repo_url": REPO_URL})
    if not resp.ok:
        print(f"Failed to start analysis: {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    job_data = resp.json()
    job_id = job_data["id"]
    print(f"Analysis Job Started: {job_id}")
    
    # 2. Poll Status
    status = "pending"
    while status not in ["completed", "failed"]:
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if not resp.ok:
            print(f"Failed to get job status: {resp.status_code}")
            continue
            
        job_data = resp.json()
        status = job_data["status"]
        progress = job_data.get("progress_message") or "..."
        analyzed = job_data.get("analyzed_files")
        total = job_data.get("total_files")
        
        print(f"[{int(time.time() - start_time)}s] Status: {status} ({analyzed}/{total}) - {progress}")
    
    # 3. Check Result
    end_time = time.time()
    print(f"Analysis Finished in {end_time - start_time:.2f}s with status: {status}")
    
    if status == "failed":
        print(f"Error Message: {job_data.get('error_message')}")
        sys.exit(1)
        
    # 4. Get Metrics
    resp = requests.get(f"{BASE_URL}/jobs/{job_id}/metrics")
    if resp.ok:
        metrics_data = resp.json()
        metrics = metrics_data.get("metrics", [])
        print(f"\n--- Discovered {len(metrics)} Metrics ---")
        for m in metrics:
            print(f"- {m['name']} ({m['category']}): {m['description'][:100]}...")
    else:
        print(f"Failed to fetch metrics: {resp.status_code}")

if __name__ == "__main__":
    test_analyze_flow()
