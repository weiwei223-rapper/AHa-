"""AI-powered video content analyzer using Gemini plus YouTube transcripts."""

from __future__ import annotations

import json
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
    from . import schema
except ImportError:
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
    "right", "okay", "well", "need", "want", "like", "code", "python", "video",
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
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.5,
                    "maxOutputTokens": 2048,
                },
            },
            timeout=30,
        )
        if not response.ok:
            raise ValueError(
                f"Gemini API error {response.status_code} for model '{model_name}': {response.text}"
            )

        response.encoding = 'utf-8'
        data = response.json()

        if 'error' in data:
            raise ValueError(f"Gemini API error: {data['error']}")

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates returned from Gemini: {data}")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise ValueError(f"No content parts returned from Gemini: {data}")

        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise ValueError(f"Empty text returned from Gemini: {data}")

        return text

    except requests.exceptions.Timeout:
        raise ValueError("Gemini API request timed out")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gemini API request failed: {e}")
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid response from Gemini API: {e}")


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    prompt = "Reply with exactly: GEMINI_OK"
    text = generate_text_with_gemini(
        [{"role": "user", "parts": [{"text": prompt}]}],
        model=model,
    )
    return {
        "ok": text.strip() == "GEMINI_OK",
        "model": model,
        "reply": text.strip(),
    }


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
        _whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _whisper_model


def _download_audio_track(video_link: str, target_dir: Path) -> Path:
    output_template = str(target_dir / "%(id)s.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
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
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    return re.sub(r"\s+", " ", text).strip()


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
        transcript = YouTubeTranscriptApi().fetch(
            video_id,
            languages=TRANSCRIPT_LANGUAGES,
            preserve_formatting=False,
        )
    except YouTubeTranscriptApiException as exc:
        print(f"Transcript unavailable for {video_link}: {exc}")
        return transcribe_video_audio(video_link, max_chars=max_chars)
    except Exception as exc:
        print(f"Unexpected transcript error for {video_link}: {exc}")
        return transcribe_video_audio(video_link, max_chars=max_chars)

    text = _stringify_transcript_items(transcript)
    text = re.sub(r"\s+", " ", text).strip()
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
            blocks.append(
                f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt:\n{transcript}"
            )
        else:
            blocks.append(
                f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt unavailable."
            )
    return "\n\n".join(blocks)


def _extract_keywords(text: str, limit: int = 6) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
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
        return "目前沒有可用的影片逐字稿。"

    snippets = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    snippets = [snippet.strip() for snippet in snippets if snippet.strip()]
    summary = " ".join(snippets[:4]).strip()
    return summary[:600] if summary else cleaned[:600]


def generate_transcript_fallback_reply(message: str, videos: list[dict] | None = None) -> str:
    available_videos = videos or []
    selected = _pick_relevant_video(message, available_videos)
    if not selected:
        return "目前沒有可參考的影片內容，請先上傳影片，或直接描述你想討論的主題。"

    title = str(selected.get("title") or "未命名影片").strip()
    link = str(selected.get("video_link") or "").strip()
    transcript = fetch_video_transcript(link, max_chars=MAX_CHAT_TRANSCRIPT_CHARS)

    if not transcript:
        return f"我目前還抓不到《{title}》的逐字稿內容。你可以先重新整理或換一支可取得字幕的影片，再來詢問更精準的問題。"

    summary = _summarize_transcript(transcript)
    keywords = _extract_keywords(transcript)
    keyword_text = f"關鍵詞：{', '.join(keywords[:5])}。" if keywords else ""
    return f"我先根據《{title}》的影片內容整理重點：{summary} {keyword_text}".strip()


def generate_chat_reply(message: str, history: list[dict], videos: list[dict] | None = None) -> str:
    video_context = build_video_context(videos or [])
    system_prompt = (
        "You are the AHa study assistant. "
        "Always answer in Traditional Chinese (繁體中文). "
        "Keep answers clear and concise. "
        "If uploaded video transcript context is available, use it to provide relevant information. "
        "Do not copy long passages from transcripts directly. "
        "If you cannot answer based on available context, provide general helpful study advice."
    )

    contents = [{"role": "system", "parts": [{"text": system_prompt}]}]

    if video_context:
        contents.append(
            {"role": "system", "parts": [{"text": f"Uploaded video context:\n{video_context}"}]}
        )

    for item in history:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        contents.append(
            {
                "role": "assistant" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )

    contents.append({"role": "user", "parts": [{"text": message.strip()}]})

    for model in [DEFAULT_GEMINI_MODEL, "gemini-3.5-pro", "gemini-1.5-flash"]:
        try:
            reply = generate_text_with_gemini(contents, model)
            print(f"Generated reply successfully with {model}: {reply[:50]}...")
            if not reply or len(reply.strip()) < 10:
                continue
            return reply.strip()
        except Exception as e:
            print(f"Gemini model {model} failed: {e}")
            continue

    print("All Gemini models failed for chat reply")
    return "抱歉，聊天服務暫時無法使用。請稍後再試。"


def analyze_video_content_with_ai(video_link: str, title: str) -> list[schema.QuizQuestion]:
    transcript = fetch_video_transcript(video_link)
    prompt = f"""
You are a Python code completion quiz designer. Based on the video content, generate 5 "fill-in-the-blank" questions.
Each question should provide a code snippet with a `___` placeholder that the user needs to fill.

Video Title: {title}
Video Link: {video_link}
Full Transcript:
{transcript or "Transcript unavailable."}

Output requirements:
1. Generate exactly 5 fill-in-the-blank questions.
2. Questions MUST use syntax, concepts, or logic mentioned in the video.
3. Include these fields in every item:
   - question: string describing the task and including the code snippet with `___`
   - correct_answer: the exact string that replaces `___`
   - explanation: short Traditional Chinese explanation mentioning the video context
   - starter_code: the full code snippet including `___`
4. If transcript is unavailable, base questions on the "Video Title" ({title}).
5. Return ONLY a valid JSON array.

Example:
{{
  "question": "根據影片教學，如何定義一個名為 greet 的函式？\\n\\n```python\\n___ greet():\\n    print('Hello')\\n```",
  "correct_answer": "def",
  "explanation": "影片中介紹了使用 def 關鍵字來定義函式。",
  "starter_code": "___ greet():\\n    print('Hello')"
}}
"""
    try:
        response_text = generate_text_with_gemini(
            [{"role": "user", "parts": [{"text": prompt}]}]
        )
        quiz_data = parse_ai_response(response_text)
        return [
            schema.QuizQuestion(
                question=item.get("question", ""),
                correct_answer=item.get("correct_answer", ""),
                explanation=item.get("explanation"),
                starter_code=item.get("starter_code"),
            )
            for item in quiz_data
        ]
    except Exception as exc:
        print(f"Error analyzing video with AI: {exc}")
        return generate_fallback_questions(title)


def parse_ai_response(response_text: str) -> list[dict]:
    start_idx = response_text.find("[")
    end_idx = response_text.rfind("]") + 1
    if start_idx == -1 or end_idx == 0:
        raise ValueError("No JSON array found in response")

    quiz_data = json.loads(response_text[start_idx:end_idx])
    if not isinstance(quiz_data, list) or len(quiz_data) == 0:
        raise ValueError("Invalid quiz data structure")

    for item in quiz_data:
        if not all(key in item for key in ["question", "correct_answer"]):
            raise ValueError("Missing required fields in question")
        if not isinstance(item["correct_answer"], str):
            raise ValueError("Each correct_answer must be a string")
    return quiz_data


def generate_fallback_questions(title: str) -> list[schema.QuizQuestion]:
    return [
        schema.QuizQuestion(
            question="請填補以下程式碼以檢查字串是否為迴文：\n\n```python\ndef is_palindrome(s):\n    return s == ___ \n```",
            correct_answer="s[::-1]",
            explanation="使用字串切片 [::-1] 來反轉字串是檢查迴文的常見做法。",
            starter_code="def is_palindrome(s):\n    return s == ___",
        ),
        schema.QuizQuestion(
            question="請填補以下程式碼以過濾列表中的偶數：\n\n```python\ndef get_evens(nums):\n    return [x for x in nums if ___]\n```",
            correct_answer="x % 2 == 0",
            explanation="使用 x % 2 == 0 來判斷一個數字是否為偶數。",
            starter_code="def get_evens(nums):\n    return [x for x in nums if ___]",
        ),
        schema.QuizQuestion(
            question="請使用正確的方法移除字串兩端的空白：\n\n```python\ntext = '  hello  '\nclean_text = text.___()\n```",
            correct_answer="strip",
            explanation="Python 的 strip() 方法可以用於移除字串開頭與結維的空白字元。",
            starter_code="text = '  hello  '\nclean_text = text.___()",
        ),
        schema.QuizQuestion(
            question="如何將字串轉換為整數？\n\n```python\nnum_str = '123'\nnum = ___(num_str)\n```",
            correct_answer="int",
            explanation="int() 函式可以將符合格式的字串或浮點數轉換為整數。",
            starter_code="num_str = '123'\nnum = ___(num_str)",
        ),
        schema.QuizQuestion(
            question="請填入正確的關鍵字以在迴圈中跳過當前疊代：\n\n```python\nfor i in range(10):\n    if i % 2 == 0:\n        ___\n    print(i)\n```",
            correct_answer="continue",
            explanation="continue 關鍵字用於跳過當前迴圈的剩餘部分，直接進入下一次疊代。",
            starter_code="for i in range(10):\n    if i % 2 == 0:\n        ___\n    print(i)",
        ),
    ]
