import os
import requests
import json
import re
from typing import Optional, List, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv

# Configuration
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


STOPWORDS = {"the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "from", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once"}
GREETING_WORDS = {"大家好", "歡迎來到", "我是", "上次影片", "今天我們", "嗨", "hello", "hi", "談到", "談過", "講過"}

def init_gemini() -> str:
    # 優先載入專屬金鑰檔
    env_path = os.path.join(os.path.dirname(__file__), "API_key.env")
    load_dotenv(env_path)
    # 也嘗試載入標準 .env
    load_dotenv()
    
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


def fetch_video_transcript(video_link: str) -> str:
    """Fetch transcript from YouTube or other sources."""
    video_id = extract_youtube_video_id(video_link)
    if not video_id:
        return ""

    try:
        # 實例化 API 類別（在此版本中為實例方法）
        api = YouTubeTranscriptApi()
        data = api.fetch(
            video_id, 
            languages=['zh-TW', 'zh-Hant', 'zh-Hans', 'zh', 'en']
        )
        # 在此版本中，data 是物件列表，需使用 .text 訪問
        return " ".join([item.text for item in data])
    except Exception as e:
        print(f"Transcript fetch failed for {video_id}: {e}")
        # 嘗試不指定語言
        try:
            api = YouTubeTranscriptApi()
            data = api.fetch(video_id)
            return " ".join([item.text for item in data])
        except Exception as e2:
            print(f"Default transcript fetch also failed: {e2}")
            return ""


def extract_youtube_video_id(video_link: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([^&#]+)",
        r"(?:youtu\.be/)([^?&#]+)",
        r"(?:youtube\.com/embed/)([^?&#]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, video_link)
        if match:
            return match.group(1)
    return None


def _extract_transcript_snippets(transcript: str, limit: int = 5) -> list[str]:
    raw_snippets = re.split(r"(?<=[.!?。！？])\s+|\n+", transcript)
    cleaned: list[str] = []
    seen: set[str] = set()
    
    for snippet in raw_snippets:
        normalized = re.sub(r"\s+", " ", snippet).strip(" -\t\r\n")
        if len(normalized) < 30:
            continue
        greeting_count = sum(1 for word in GREETING_WORDS if word in normalized)
        if greeting_count > 1 and len(normalized) < 60:
            continue
        if any(normalized.startswith(word) for word in {"嗨", "大家", "各位", "今天"}):
            if len(normalized) < 50:
                continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized[:200])
        if len(cleaned) >= limit:
            break
    return cleaned


def _pick_answer_from_snippet(snippet: str) -> str:
    tech_keywords = ["bool", "int", "float", "str", "list", "dict", "tuple", "set", 
                     "while", "for", "if", "else", "elif", "return", "def", "class",
                     "True", "False", "None", "and", "or", "not", "is", "in"]
    for kw in tech_keywords:
        if f" {kw} " in f" {snippet} " or f"『{kw}』" in snippet or f"({kw})" in snippet:
            return kw
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", snippet)
    filtered = [word for word in words if word.lower() not in STOPWORDS]
    return filtered[0] if filtered else "value"


def generate_fallback_questions(
    title: str,
    transcript: str = "",
    outline: str = "",
) -> list[Any]:
    from . import schema
    snippets = _extract_transcript_snippets(transcript, limit=8)
    if not snippets:
        snippets = [outline[:100]] if outline else [title]
        
    questions = []
    used_answers = set()

    for snippet in snippets:
        if len(questions) >= 5: break
        answer = _pick_answer_from_snippet(snippet)
        if answer.lower() in used_answers or len(answer) < 2: continue
        used_answers.add(answer.lower())
        
        starter_code = f"result = ___\n# 根據影片描述，此處應填入 {answer}\nprint(result)"
        
        questions.append(
            schema.QuizQuestion(
                question=f"根據影片內容提到『{answer}』的應用。請補全程式碼使其能正確表示該概念。",
                correct_answer=answer,
                explanation=f"根據影片描述：『{snippet[:60]}...』",
                reference_concept="Python 基礎應用",
                question_type="fill-in-the-blank",
                source_time="unknown",
                starter_code=starter_code,
                test_cases=[f"print({repr(answer)})"]
            )
        )
    return questions


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    text = generate_text_with_gemini([{"role": "user", "parts": [{"text": "Reply with exactly: GEMINI_OK"}]}], model=model)
    return {"ok": text.strip() == "GEMINI_OK", "model": model, "reply": text.strip()}
