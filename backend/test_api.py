
import os
import requests
from dotenv import load_dotenv

def test_gemini():
    load_dotenv('API_key.env')
    api_key = os.getenv('AI_API_KEY')
    model = "gemini-2.5-flash" # The model from environment or default
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": "Hello, are you there?"}]
        }]
    }
    
    print(f"Testing Gemini API with model: {model}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.ok:
            print("Response:", response.json()['candidates'][0]['content']['parts'][0]['text'])
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_gemini()
