import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app

THRESHOLD_MS = 500.0
RUNS = 30


def benchmark_endpoint(client: TestClient, path: str) -> dict[str, float]:
    samples = []
    for _ in range(RUNS):
        start = time.perf_counter()
        response = client.get(path)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if response.status_code != 200:
            raise RuntimeError(f"{path} returned unexpected status {response.status_code}")
        samples.append(elapsed_ms)
    return {
        "avg": statistics.mean(samples),
        "p95": sorted(samples)[int(RUNS * 0.95) - 1],
        "max": max(samples),
    }


def main() -> None:
    with TestClient(app) as client:
        videos_result = benchmark_endpoint(client, "/videos")
        quizzes_result = benchmark_endpoint(client, "/quizzes")

    print("Performance report (ms)")
    print(f"/videos: avg={videos_result['avg']:.2f} p95={videos_result['p95']:.2f} max={videos_result['max']:.2f}")
    print(f"/quizzes: avg={quizzes_result['avg']:.2f} p95={quizzes_result['p95']:.2f} max={quizzes_result['max']:.2f}")

    if videos_result["p95"] > THRESHOLD_MS or quizzes_result["p95"] > THRESHOLD_MS:
        raise SystemExit(f"Performance check failed: p95 exceeds {THRESHOLD_MS}ms")

    print(f"PASS: p95 latency is under {THRESHOLD_MS}ms")


if __name__ == "__main__":
    main()
