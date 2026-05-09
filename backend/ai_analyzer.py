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
        return text
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gemini API request failed: {str(e)}")
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
        response = generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])
        return "VALID" in response.upper()
    except:
        # 如果 AI 判斷失敗，預設允許通過以避免誤殺
        return True


def get_video_title(video_link: str) -> Optional[str]:
    """Resiliently fetch the actual YouTube video title."""
    # 方法 1: 使用 yt-dlp (最全面，但易被擋)
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

    # 方法 2: 直接爬取 HTML (輕量級，不易被擋)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(video_link, headers=headers, timeout=10)
        if response.ok:
            # 找 <title> 標籤
            title_match = re.search(r"<title>(.*?)</title>", response.text)
            if title_match:
                raw_title = title_match.group(1)
                # 移除 " - YouTube" 尾綴
                return raw_title.replace(" - YouTube", "").strip()
    except:
        pass
    
    return None


def fetch_video_transcript(video_link: str) -> str:
    """Fetch transcript using YouTube API. Return empty if no subtitles found to trigger Title Fallback."""
    video_id = extract_youtube_video_id(video_link)
    if not video_id:
        return ""

    print(f"DEBUG: Attempting to fetch subtitles for {video_id}...")
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # 1. 優先找繁體中文 (zh-TW, zh-Hant)
        try:
            transcript = transcript_list.find_transcript(['zh-TW', 'zh-Hant'])
        except:
            # 2. 找其他形式的中文
            try:
                transcript = transcript_list.find_transcript(['zh-Hans', 'zh', 'zh-CN'])
            except:
                # 3. 找英文並自動翻譯成繁中
                try:
                    transcript = transcript_list.find_transcript(['en']).translate('zh-TW')
                except:
                    # 4. 隨便抓一個可用的並翻譯
                    transcript = next(iter(transcript_list)).translate('zh-TW')

        data = transcript.fetch()
        result = " ".join([item.text for item in data])
        print(f"DEBUG: Successfully fetched subtitles ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"DEBUG: No subtitles found on YouTube for {video_id}: {e}")
        # 回傳空字串，這會觸發 learning_pipeline.py 中的「標題推理專家模式」
        return ""



def _transcribe_with_whisper(video_link: str) -> str:
    """Download audio and use Whisper to transcribe with Anti-Bot bypass."""
    _setup_ffmpeg()
    
    video_id = extract_youtube_video_id(video_link)
    clean_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else video_link

    with tempfile.TemporaryDirectory() as temp_dir:
        # 強力偽裝下載參數
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
            'ffmpeg_location': FFMPEG_PATH,
            'noplaylist': True,
            'nocheckcertificate': True,
            # 偽裝成一般的 Chrome 瀏覽器
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
            # 關鍵：嘗試從本地瀏覽器借用 Cookie 繞過機器人驗證 (支援 Chrome, Edge)
            'cookiesfrombrowser': ('chrome', 'edge'), 
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
            'no_warnings': False,
        }

        print(f"DEBUG: Starting ARMORED audio download for {clean_url}...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clean_url])
        except Exception as dl_err:
            print(f"DEBUG: Armored download failed: {dl_err}. YouTube security is very strong.")
            raise dl_err

        audio_path = os.path.join(temp_dir, 'audio.mp3')
        if not os.path.exists(audio_path):
            print(f"DEBUG: audio.mp3 not found at {audio_path}")
            raise FileNotFoundError("Audio extraction failed")

        print("DEBUG: Initializing Whisper AI model (tiny)...")
        # 增加載入模型時的錯誤捕捉
        try:
            model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type="float32")
        except Exception as model_err:
            print(f"DEBUG: Whisper model load failed: {model_err}")
            raise model_err
        
        print("DEBUG: Transcribing audio (this may take a while)...")
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        # 遍歷 segments 時印出進度
        transcript_parts = []
        for i, segment in enumerate(segments):
            transcript_parts.append(segment.text)
            if i % 10 == 0:
                print(f"DEBUG: Transcribing... segment {i}")
        
        transcript_text = " ".join(transcript_parts)
        print(f"DEBUG: AI Transcription complete. Detected language: {info.language}")
        return transcript_text


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
