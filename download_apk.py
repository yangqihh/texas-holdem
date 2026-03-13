import requests
import os
import sys
import time

TOKEN = "y-kBBF9IATfnQZXueQpi"
PROJECT = "horryyang/texas-holdem"
ENCODED = requests.utils.quote(PROJECT, safe='')
BASE_URL = f"https://git.woa.com/api/v3/projects/{ENCODED}"
HEADERS = {"PRIVATE-TOKEN": TOKEN}
DEST_DIR = r"Z:\texas-holdem"

def get_latest_pipeline():
    """尝试多种API路径获取最新流水线"""
    paths = [
        f"{BASE_URL}/pipelines?per_page=1&order_by=id&sort=desc",
        f"https://git.woa.com/api/v4/projects/{ENCODED}/pipelines?per_page=1",
    ]
    for url in paths:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()
            if isinstance(data, list) and data:
                return data[0]
        except:
            pass
    return None

def get_jobs(pipeline_id):
    r = requests.get(f"{BASE_URL}/pipelines/{pipeline_id}/jobs", headers=HEADERS, timeout=10)
    return r.json() if r.ok else []

def download_artifacts(job_id, dest):
    url = f"{BASE_URL}/jobs/{job_id}/artifacts"
    r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
    if r.ok:
        zip_path = os.path.join(dest, "artifacts.zip")
        os.makedirs(dest, exist_ok=True)
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        # Unzip
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(dest)
        os.remove(zip_path)
        # Find APKs
        apks = []
        for root, dirs, files in os.walk(dest):
            for f in files:
                if f.endswith('.apk'):
                    apks.append(os.path.join(root, f))
        return apks
    return []

def main():
    print(f"[APK Downloader] Checking CI status for {PROJECT}")
    
    pipeline = get_latest_pipeline()
    if not pipeline:
        print("No pipeline found. CI may not have started yet.")
        print("Please check: https://git.woa.com/horryyang/texas-holdem/-/pipelines")
        sys.exit(1)
    
    pid = pipeline.get('id')
    status = pipeline.get('status')
    print(f"Latest pipeline #{pid}: {status}")
    
    if status == 'success':
        jobs = get_jobs(pid)
        for job in jobs:
            if job.get('status') == 'success' and job.get('artifacts_file'):
                apks = download_artifacts(job['id'], DEST_DIR)
                if apks:
                    print(f"APK downloaded to: {', '.join(apks)}")
                    sys.exit(0)
        print("Pipeline succeeded but no APK artifact found.")
        sys.exit(2)
    elif status in ('running', 'pending'):
        print(f"CI still {status}. Check back later.")
        sys.exit(3)
    else:
        print(f"Pipeline status: {status}. May need manual check.")
        sys.exit(4)

if __name__ == '__main__':
    main()
