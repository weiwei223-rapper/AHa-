
import os
import requests
from dotenv import load_dotenv

def list_models():
    load_dotenv('API_key.env')
    api_key = os.getenv('AI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print("Listing available models...")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.ok:
            models = response.json().get('models', [])
            for m in models:
                print(f"- {m['name']} (supported: {m['supportedGenerationMethods']})")
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_models()
