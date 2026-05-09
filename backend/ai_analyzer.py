import os
import requests
import json
from typing import Optional

# Configuration
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def init_gemini() -> str:
    api_key = (os.getenv("AI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("AI_API_KEY not found in environment variables")
    return api_key


def generate_text_with_gemini(contents: list[dict], model: str = DEFAULT_GEMINI_MODEL) -> str:
    api_key = init_gemini()
    model_name = model.replace("models/", "")
    
    system_parts: list[dict] = []
    gemini_contents: list[dict] = []
    for item in contents:
        role = item.get("role", "user")
        parts = item.get("parts", [])
        if role == "system":
            system_parts.extend(parts)
            continue
        gemini_contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": parts,
            }
        )

    request_payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": 0.5, 
            "maxOutputTokens": 8192,
            "topP": 0.95,
            "topK": 40
        },
    }
    if system_parts:
        request_payload["systemInstruction"] = {"parts": system_parts}

    try:
        response = requests.post(
            GEMINI_API_URL.format(model=model_name),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json=request_payload,
            timeout=120,
        )
        if not response.ok:
            raise ValueError(f"Gemini API error {response.status_code} for model '{model_name}': {response.text}")
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates returned from Gemini: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError(f"No content parts returned from Gemini: {data}")
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise ValueError("Empty response text from Gemini")
        return text
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gemini API request failed: {str(e)}")


def analyze_code(code: str, language: str) -> str:
    prompt = f"""You are an expert programmer. Analyze the following {language} code and provide:
1. A brief summary of what the code does.
2. Potential issues or bugs.
3. Suggestions for optimization or improvement.

Code:
```{language}
{code}
```"""
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    return generate_text_with_gemini(contents)


def generate_learning_content(topic: str, context: Optional[str] = None) -> str:
    prompt = f"Explain the concept of '{topic}' in the context of computer science and programming."
    if context:
        prompt += f"\nAdditional context: {context}"
    prompt += "\nProvide a clear explanation with examples where appropriate."
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    return generate_text_with_gemini(contents)


def generate_quiz(content: str, num_questions: int = 5) -> list[dict]:
    prompt = f"""Based on the following content, generate {num_questions} multiple-choice questions for a quiz.
Each question should have 4 options and exactly one correct answer.
Format the output as a JSON array of objects, where each object has:
- question: The question text
- options: An array of 4 strings
- correct_answer: The index of the correct option (0-3)
- explanation: A brief explanation of the correct answer

Content:
{content}
"""
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    response_text = generate_text_with_gemini(contents)
    
    # Extract JSON if the model wrapped it in markdown
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
        
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: try to find something that looks like a JSON array
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start != -1 and end != 0:
            try:
                return json.loads(response_text[start:end])
            except:
                pass
        raise ValueError("Failed to parse quiz JSON from Gemini response")

def get_chat_response(messages: list[dict], model: str = DEFAULT_GEMINI_MODEL) -> str:
    """
    Get a response from Gemini for a list of chat messages.
    messages: List of dicts with 'role' (user/assistant/system) and 'content' (str)
    """
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Gemini expects 'parts' to be a list of dictionaries with 'text'
        contents.append({
            "role": role,
            "parts": [{"text": content}]
        })
    
    return generate_text_with_gemini(contents, model=model)
