
import requests
import time

def trigger_quiz():
    url = "http://127.0.0.1:8001/api/videos/20/quiz"
    params = {"user_id": 1}
    print(f"Triggering quiz generation for video 20...")
    try:
        start_time = time.time()
        response = requests.get(url, params=params, timeout=60)
        end_time = time.time()
        print(f"Status Code: {response.status_code}")
        print(f"Time taken: {end_time - start_time:.2f}s")
        if response.ok:
            data = response.json()
            print(f"Quiz Type: {data.get('quiz_type')}")
            print(f"Number of questions: {len(data.get('questions', []))}")
            for i, q in enumerate(data.get('questions', []), 1):
                print(f"Q{i}: {q.get('question')[:50]}...")
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    trigger_quiz()
