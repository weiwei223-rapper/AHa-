"""AI-powered video content analyzer using Gemini plus YouTube transcripts."""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

import requests
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import YouTubeTranscriptApiException
from yt_dlp import YoutubeDL

try:
    from . import question_bank, schema
except ImportError:
    import question_bank
    import schema

BASE_DIR = os.path.dirname(__file__)
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TRANSCRIPT_LANGUAGES = ("zh-TW", "zh-Hant", "zh-CN", "zh", "en")
MAX_TRANSCRIPT_CHARS = 12000
MAX_CHAT_TRANSCRIPT_CHARS = 2200
MAX_CONTEXT_VIDEOS = 3
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
CACHE_DIR = Path(BASE_DIR) / ".cache"
TRANSCRIPT_CACHE_DIR = CACHE_DIR / "transcripts"
DOWNLOAD_CACHE_DIR = CACHE_DIR / "downloads"
STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "will", "your", "what",
    "about", "they", "them", "then", "here", "there", "into", "would", "could",
    "should", "were", "been", "being", "when", "where", "which", "while", "because",
    "just", "than", "also", "only", "some", "more", "most", "very", "much", "now",
    "right", "okay", "well", "need", "want", "like", "video", "python",
}

load_dotenv(dotenv_path=os.path.join(BASE_DIR, "API_key.env"))
TRANSCRIPT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_whisper_model: WhisperModel | None = None


def init_gemini() -> str:
    api_key = (os.getenv("AI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("AI_API_KEY not found in environment variables")
    return api_key


def generate_text_with_gemini(contents: list[dict], model: str = DEFAULT_GEMINI_MODEL) -> str:
    api_key = init_gemini()
    model_name = model.replace("models/", "")
    try:
        response = requests.post(
            GEMINI_API_URL.format(model=model_name),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.5,
                    "maxOutputTokens": 8192,
                    "topP": 0.95,
                    "topK": 40
                },
            },
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
            raise ValueError(f"Empty text returned from Gemini: {data}")
        return text
    except requests.exceptions.Timeout:
        raise ValueError("Gemini API request timed out")
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Gemini API request failed: {exc}")


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    text = generate_text_with_gemini([{"role": "user", "parts": [{"text": "Reply with exactly: GEMINI_OK"}]}],
                                     model=model)
    return {"ok": text.strip() == "GEMINI_OK", "model": model, "reply": text.strip()}


def extract_youtube_video_id(video_link: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([^&#]+)",
        r"(?:youtu\.be/)([^?&#]+)",
        r"(?:youtube\.com/embed/)([^?&#]+)",
        r"(?:youtube\.com/shorts/)([^?&#]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, video_link)
        if match:
            return match.group(1)
    return None


def _get_cached_transcript_path(video_id: str) -> Path:
    return TRANSCRIPT_CACHE_DIR / f"{video_id}.txt"


def _read_cached_transcript(video_id: str, max_chars: int) -> str:
    path = _get_cached_transcript_path(video_id)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:max_chars]
    except OSError:
        return ""


def _write_cached_transcript(video_id: str, transcript: str) -> None:
    if transcript:
        _get_cached_transcript_path(video_id).write_text(transcript, encoding="utf-8")


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    return _whisper_model


def _download_audio_track(video_link: str, target_dir: Path) -> Path:
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(target_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(video_link, download=True)
        downloaded = Path(ydl.prepare_filename(info))
        if downloaded.exists():
            return downloaded
        candidates = sorted(target_dir.glob(f"{info['id']}.*"))
        if not candidates:
            raise FileNotFoundError("Downloaded audio file not found")
        return candidates[0]


def _transcribe_audio_file(audio_path: Path) -> str:
    model = _get_whisper_model()
    segments, _ = model.transcribe(str(audio_path), vad_filter=True)
    return re.sub(r"\s+", " ", " ".join(segment.text.strip() for segment in segments if segment.text.strip())).strip()


def transcribe_video_audio(video_link: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    video_id = extract_youtube_video_id(video_link)
    if not video_id:
        return ""
    cached = _read_cached_transcript(video_id, max_chars)
    if cached:
        return cached
    try:
        with TemporaryDirectory(dir=DOWNLOAD_CACHE_DIR) as temp_dir:
            audio_path = _download_audio_track(video_link, Path(temp_dir))
            transcript = _transcribe_audio_file(audio_path)
    except Exception as exc:
        print(f"Audio transcription unavailable for {video_link}: {exc}")
        return ""
    if transcript:
        _write_cached_transcript(video_id, transcript)
    return transcript[:max_chars]


def _stringify_transcript_items(items: Iterable[object]) -> str:
    parts: list[str] = []
    for item in items:
        text = getattr(item, "text", "")
        cleaned = str(text).strip()
        if cleaned:
            parts.append(cleaned)
    return " ".join(parts)


def fetch_video_transcript(video_link: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    video_id = extract_youtube_video_id(video_link)
    if not video_id:
        return ""
    cached = _read_cached_transcript(video_id, max_chars)
    if cached:
        return cached
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=TRANSCRIPT_LANGUAGES, preserve_formatting=False)
    except YouTubeTranscriptApiException as exc:
        print(f"Transcript unavailable for {video_link}: {exc}")
        return transcribe_video_audio(video_link, max_chars=max_chars)
    except Exception as exc:
        print(f"Unexpected transcript error for {video_link}: {exc}")
        return transcribe_video_audio(video_link, max_chars=max_chars)
    text = re.sub(r"\s+", " ", _stringify_transcript_items(transcript)).strip()
    if text:
        _write_cached_transcript(video_id, text)
        return text[:max_chars]
    return transcribe_video_audio(video_link, max_chars=max_chars)


def build_video_context(videos: list[dict]) -> str:
    blocks: list[str] = []
    for index, video in enumerate(videos[:MAX_CONTEXT_VIDEOS], start=1):
        title = str(video.get("title") or "Untitled video").strip()
        link = str(video.get("video_link") or "").strip()
        transcript = fetch_video_transcript(link, max_chars=MAX_CHAT_TRANSCRIPT_CHARS)
        if transcript:
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt:\n{transcript}")
        else:
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt unavailable.")
    return "\n\n".join(blocks)


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z']{2,}", text.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def _pick_relevant_video(message: str, videos: list[dict]) -> dict | None:
    prompt = message.lower().strip()
    for video in videos:
        title = str(video.get("title") or "").lower()
        if title and title in prompt:
            return video
    return videos[0] if videos else None


def _summarize_transcript(transcript: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", " ", transcript)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "目前沒有可用的逐字稿內容。"
    snippets = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    snippets = [snippet.strip() for snippet in snippets if snippet.strip()]
    summary = " ".join(snippets[:4]).strip()
    return summary[:600] if summary else cleaned[:600]


def generate_transcript_fallback_reply(message: str, videos: list[dict] | None = None) -> str:
    available_videos = videos or []
    selected = _pick_relevant_video(message, available_videos)
    if not selected:
        return "目前沒有可參考的影片內容，請先新增影片，再問我和影片有關的問題。"
    title = str(selected.get("title") or "未命名影片").strip()
    link = str(selected.get("video_link") or "").strip()
    transcript = fetch_video_transcript(link, max_chars=MAX_CHAT_TRANSCRIPT_CHARS)
    if not transcript:
        return f"我目前還抓不到《{title}》的逐字稿，所以沒辦法可靠地根據影片內容回答。"
    summary = _summarize_transcript(transcript)
    keywords = _extract_keywords(transcript)
    keyword_text = f"關鍵字：{', '.join(keywords[:5])}" if keywords else ""
    return f"根據《{title}》目前可取得的內容，重點是：{summary} {keyword_text}".strip()


def generate_chat_reply(message: str, history: list[dict], videos: list[dict] | None = None) -> str:
    video_context = build_video_context(videos or [])
    system_prompt = (
        "You are the AHa study assistant. "
        "Always answer in Traditional Chinese. "
        "Keep answers clear and concise. "
        "If uploaded video transcript context is available, use it to provide relevant information. "
        "Do not copy long passages from transcripts directly. "
        "If you cannot answer based on available context, provide general helpful study advice."
    )
    contents = [{"role": "system", "parts": [{"text": system_prompt}]}]
    if video_context:
        contents.append({"role": "system", "parts": [{"text": f"Uploaded video context:\n{video_context}"}]})
    for item in history:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()
        if content:
            contents.append({"role": "assistant" if role == "assistant" else "user", "parts": [{"text": content}]})
    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    for model in [DEFAULT_GEMINI_MODEL, "gemini-1.5-flash"]:
        try:
            reply = generate_text_with_gemini(contents, model)
            if reply and len(reply.strip()) >= 10:
                return reply.strip()
        except Exception as exc:
            print(f"Gemini model {model} failed: {exc}")
    return "我現在無法連線到 AI 服務，但你可以先問我你想聚焦哪個影片主題，我再用已抓到的內容協助整理。"


GREETING_WORDS = {"大家好", "歡迎來到", "我是", "上次影片", "今天我們", "嗨", "hello", "hi", "談到", "談過", "講過"}


def _extract_transcript_snippets(transcript: str, limit: int = 5) -> list[str]:
    # 先把長度太短或明顯是廢話的過濾掉
    raw_snippets = re.split(r"(?<=[.!?。！？])\s+|\n+", transcript)
    cleaned: list[str] = []
    seen: set[str] = set()

    for snippet in raw_snippets:
        normalized = re.sub(r"\s+", " ", snippet).strip(" -\t\r\n")

        # 門檻 1：長度必須超過 30 個字（確保有資訊量）
        if len(normalized) < 30:
            continue

        # 門檻 2：不能包含過多招呼語
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
    # 優先找關鍵技術詞
    tech_keywords = ["bool", "int", "float", "str", "list", "dict", "tuple", "set",
                     "while", "for", "if", "else", "elif", "return", "def", "class",
                     "True", "False", "None", "and", "or", "not", "is", "in"]
    for kw in tech_keywords:
        if f" {kw} " in f" {snippet} " or f"『{kw}』" in snippet or f"({kw})" in snippet:
            return kw

    # 如果沒找到，找一段英文字
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", snippet)
    filtered = [word for word in words if word.lower() not in STOPWORDS]
    return filtered[0] if filtered else "Solution"


def generate_fallback_questions(
        title: str,
        transcript: str = "",
        outline: str = "",
        templates: list[question_bank.QuestionTemplate] | None = None,
) -> list[schema.QuizQuestion]:
    # 這裡的邏輯必須確保即使 AI 斷線，出的題目也像 LeetCode
    snippets = _extract_transcript_snippets(transcript, limit=8)
    if not snippets:
        snippets = [outline[:100]] if outline else [title]

    keyword_pool = _extract_keywords(f"{transcript}\n{outline}", limit=15)
    questions: list[schema.QuizQuestion] = []
    used_answers: set[str] = set()

    # 1. 嘗試從片段中提取「邏輯判斷」題
    for snippet in snippets:
        if len(questions) >= 5: break
        answer = _pick_answer_from_snippet(snippet)
        if answer.lower() in used_answers or len(answer) < 2: continue
        used_answers.add(answer.lower())

        starter_code = f"class Solution:\n    def validate_content(self, input_val):\n        # 補全邏輯使其符合影片描述：『{answer}』\n        # 預期：當符合該概念時回傳 True\n        return input_val == ___\n"

        questions.append(
            schema.QuizQuestion(
                question=f"影片中提到了關於『{answer}』的教學內容。請實作一個判斷函數，使其能正確識別這個關鍵概念。",
                correct_answer=answer,
                explanation=f"根據影片片段描述：『{snippet[:60]}...』，我們需要使用 {answer} 來完成邏輯。",
                reference_concept=f"Python 技術點: {answer}",
                question_type="fill-in-the-blank",
                source_time="unknown",
                source_excerpt=snippet,
                starter_code=starter_code,
                test_cases=[f"assert Solution().validate_content({repr(answer)}) == True"]
            )
        )

    # 2. 補充 LeetCode 結構題
    while len(questions) < 5 and keyword_pool:
        kw = keyword_pool.pop(0)
        if kw.lower() in used_answers or len(kw) < 3: continue
        used_answers.add(kw.lower())

        questions.append(
            schema.QuizQuestion(
                question=f"請完成一個函數，回傳本影片《{title}》中強調的核心關鍵字：{kw}。",
                correct_answer=kw,
                explanation=f"這是這段教學影片中最具代表性的詞彙之一。",
                reference_concept="課程重點回顧",
                starter_code=f"class Solution:\n    def get_key_concept(self):\n        return ___",
                test_cases=[f"assert Solution().get_key_concept() == {repr(kw)}"]
            )
        )

    return questions[:5]
