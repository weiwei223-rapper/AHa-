import os
import requests
import json
import re
import tempfile
import yt_dlp
from typing import Optional, List, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv
from faster_whisper import WhisperModel

# Configuration
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OLLAMA_API_URL = "http://localhost:11434/api/chat"
DEFAULT_OLLAMA_MODEL = "AHa-Tutor:latest"

# Whisper 語音辨識設定 (使用 tiny 模型極速辨識，適合 CPU)
WHISPER_MODEL_SIZE = "tiny"
WHISPER_DEVICE = "cpu"
FFMPEG_PATH = r"C:\Users\user\AppData\Roaming\anythingllm-desktop\storage\engines\ffmpeg\windows-x64"

STOPWORDS = {"the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "from", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once"}
GREETING_WORDS = {"大家好", "歡迎來到", "我是", "上次影片", "今天我們", "嗨", "hello", "hi", "談到", "談過", "講過"}

def _setup_ffmpeg():
    """Ensure ffmpeg is in path for the current process."""
    if FFMPEG_PATH not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + FFMPEG_PATH

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


def generate_text_with_gemini(contents: list[dict], model: str = DEFAULT_GEMINI_MODEL) -> tuple[str, dict]:
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
            timeout=300,
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
        
        usage_metadata = data.get("usageMetadata", {
            "promptTokenCount": 0,
            "candidatesTokenCount": 0,
            "totalTokenCount": 0
        })
        return text, usage_metadata
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gemini API request failed: {str(e)}")


def generate_text_with_ollama(messages: list[dict], model: str = DEFAULT_OLLAMA_MODEL) -> str:
    """Send chat history to Ollama and get a response."""
    request_payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "num_ctx": 4096,
            "min_p": 0.1,
        }
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=request_payload,
            timeout=120,
        )
        if not response.ok:
            raise ValueError(f"Ollama API error {response.status_code}: {response.text}")
        
        data = response.json()
        message = data.get("message", {})
        return message.get("content", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Ollama API request failed: {e}")
        raise ValueError(f"Ollama API request failed: {str(e)}")


def get_chat_response(messages: list[dict]) -> str:
    """Send chat history to the preferred AI (Ollama if available, else Gemini) and get a response."""
    try:
        return generate_text_with_ollama(messages)
    except Exception as e:
        print(f"DEBUG: Ollama chat failed, falling back to Gemini: {e}")

    gemini_history = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            gemini_history.append({"role": "system", "parts": [{"text": content}]})
        elif role == "assistant":
            gemini_history.append({"role": "assistant", "parts": [{"text": content}]})
        else:
            gemini_history.append({"role": "user", "parts": [{"text": content}]})
    
    text, _ = generate_text_with_gemini(gemini_history)
    return text


def is_python_related(title: str, transcript: str) -> bool:
    """Use Gemini to determine if the content is related to Python programming."""
    prompt = f"""
請判斷以下影片內容是否與「Python 程式設計」有關。
這包括：Python 語法、開發環境、資料科學、自動化腳本、Web 開發 (Django/Flask) 或任何 Python 相關教學。

影片標題：{title}
影片內容摘要：{transcript[:1000]}

要求：
1. 如果有關聯，請回傳：VALID
2. 如果無關聯（例如是單純的音樂、生活 VLOG、非 Python 的語言教學），請回傳：INVALID
3. 僅回傳以上兩個關鍵字之一，不要有其他文字。
"""
    try:
        response_text, _ = generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])
        decision = response_text.strip().upper()
        print(f"DEBUG: Video validation AI response: '{decision}'")
        
        if "INVALID" in decision:
            return False
        return "VALID" in decision
    except Exception as e:
        print(f"DEBUG: Video validation AI failed: {e}")
        return True


def get_video_title(video_link: str) -> Optional[str]:
    """Resiliently fetch the actual YouTube video title."""
    _setup_ffmpeg()
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'extract_flat': True,
        'cookiesfrombrowser': ('chrome', 'edge'),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_link, download=False)
            t = info.get("title")
            if t and "Unknown" not in t: return t
    except:
        pass

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(video_link, headers=headers, timeout=10)
        if response.ok:
            title_match = re.search(r"<title>(.*?)</title>", response.text)
            if title_match:
                raw_title = title_match.group(1)
                return raw_title.replace(" - YouTube", "").strip()
    except:
        pass
    
    return None


def fetch_video_transcript(video_link: str) -> str:
    """Fetch transcript using YouTube API."""
    video_id = extract_youtube_video_id(video_link)
    if not video_id:
        return ""

    print(f"DEBUG: Attempting to fetch subtitles for {video_id}...")
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['zh-TW', 'zh-Hant'])
        except:
            try:
                transcript = transcript_list.find_transcript(['zh-Hans', 'zh', 'zh-CN'])
            except:
                try:
                    transcript = transcript_list.find_transcript(['en']).translate('zh-TW')
                except:
                    transcript = next(iter(transcript_list)).translate('zh-TW')

        data = transcript.fetch()
        result = " ".join([item.text for item in data])
        print(f"DEBUG: Successfully fetched subtitles ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"DEBUG: No subtitles found on YouTube for {video_id}: {e}")
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
    count: int = 5
) -> list[Any]:
    try:
        from . import schema
    except ImportError:
        import schema
    snippets = _extract_transcript_snippets(transcript, limit=max(8, count))
    if not snippets:
        snippets = [outline[:100]] if outline else [title]
        
    questions = []
    used_answers = set()

    for snippet in snippets:
        if len(questions) >= count: break
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


def validate_error_report(report_content: str, source_content: str, report_type: str) -> tuple[bool, str]:
    """
    使用 AI 判斷錯誤回報是否屬實，並返回判定結果與理由。
    report_type: 'outline' (大綱/分析) 或 'quiz' (題目)
    """
    prompt = f"""
你是一個公正的品質審核員。使用者針對 AI 生成的「{ "大綱/分析" if report_type == "outline" else "測驗題目" }」提交了錯誤回報。
請根據提供的「原始生成內容」與「使用者回報內容」，判斷該回報是否「符合邏輯且屬實」。

原始生成內容：
{source_content[:3000]}

使用者回報內容：
{report_content}

判斷標準：
1. 如果使用者指出的錯誤確實存在（例如：題目答案錯誤、程式碼邏輯有誤、大綱與影片內容完全無關、翻譯嚴重錯誤等），判定為：VALID
2. 如果使用者的回報不符合事實、純屬無理取鬧、或是回報內容過於簡短無意義，判定為：INVALID
3. 注意：如果回報是關於「AI 聊天對話的回答不滿意」或是「測驗批改分數 (Grade) 不公」，這些不屬於退款範圍，判定為：INVALID。

請以 JSON 格式回傳：
{{
  "decision": "VALID" 或 "INVALID",
  "reason": "一段簡短的繁體中文說明判定理由 (20-50字)"
}}
"""
    try:
        response_text, _ = generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])
        # 嘗試從回應中提取 JSON
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            decision = data.get("decision", "INVALID").strip().upper()
            reason = data.get("reason", "經系統初步審核判定。")
            is_valid = "VALID" in decision and "INVALID" not in decision
            return is_valid, reason
        
        # Fallback if JSON fails
        is_valid = "VALID" in response_text.upper() and "INVALID" not in response_text.upper()
        return is_valid, "經 AI 系統分析判定。"
    except Exception as e:
        print(f"DEBUG: Error report validation AI failed: {e}")
        return False, "系統暫時無法處理您的回報，請稍後再試。"


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    text, _ = generate_text_with_gemini([{"role": "user", "parts": [{"text": "Reply with exactly: GEMINI_OK"}]}], model=model)
    return {"ok": text.strip() == "GEMINI_OK", "model": model, "reply": text.strip()}


def test_ollama_connection(model: str = DEFAULT_OLLAMA_MODEL) -> dict:
    """Test connection to Ollama server."""
    try:
        reply = generate_text_with_ollama([{"role": "user", "content": "Reply with exactly: OLLAMA_OK"}], model=model)
        return {"ok": reply == "OLLAMA_OK", "model": model, "reply": reply}
    except Exception as e:
        return {"ok": False, "model": model, "error": str(e)}
