import os
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://webapp:8000")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))


def simulate():
    try:
        response = requests.get(f"{WEBAPP_URL}/simulate", timeout=5)
        if response.ok:
            print(f"[✓] Session: {response.json().get('session_id')}")
        else:
            print(f"[!] Failed: {response.status_code}")
    except Exception as e:
        print(f"[X] Error: {e}")


if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    while True:
        futures = [executor.submit(simulate)
                   for _ in range(random.randint(3, MAX_WORKERS))]
        for future in as_completed(futures):
            pass  # just wait for completion
        time.sleep(random.uniform(2, 4))
