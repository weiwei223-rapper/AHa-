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
    "right", "okay", "well", "need", "want", "like", "video",
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

        data = response.json()
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
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Gemini API request failed: {exc}")


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    prompt = "Reply with exactly: GEMINI_OK"
    text = generate_text_with_gemini(
        [{"role": "user", "parts": [{"text": prompt}]}],
        model=model,
    )
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
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt:\n{transcript}")
        else:
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt unavailable.")
    return "\n\n".join(blocks)


def _extract_keywords(text: str, limit: int = 6) -> list[str]:
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
        if not content:
            continue
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


def _extract_transcript_snippets(transcript: str, limit: int = 5) -> list[str]:
    snippets = re.split(r"(?<=[.!?。！？])\s+|\n+", transcript)
    cleaned: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        normalized = re.sub(r"\s+", " ", snippet).strip(" -\t\r\n")
        if len(normalized) < 18:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized[:120])
        if len(cleaned) >= limit:
            break
    return cleaned


def _pick_answer_from_snippet(snippet: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z']{2,}", snippet)
    filtered = [word for word in words if word.lower() not in STOPWORDS]
    if filtered:
        return filtered[-1]
    compact = re.sub(r"[^A-Za-z0-9]+", " ", snippet).strip()
    return compact.split()[-1] if compact else "value"


def _dynamic_fallback_questions(transcript: str, outline: str) -> list[schema.QuizQuestion]:
    snippets = _extract_transcript_snippets(transcript, limit=5)
    if not snippets:
        snippets = _extract_transcript_snippets(outline, limit=5)

    questions: list[schema.QuizQuestion] = []
    used_answers: set[str] = set()
    for index, snippet in enumerate(snippets, start=1):
        answer = _pick_answer_from_snippet(snippet)
        if answer.lower() in used_answers:
            continue
        used_answers.add(answer.lower())
        variable_name = f"video_fact_{index}"
        questions.append(
            schema.QuizQuestion(
                question=f"根據影片內容，補上最符合這段描述的關鍵字。\n\n```python\n{variable_name} = \"___\"\n```",
                correct_answer=answer,
                explanation="這題直接根據影片片段抽取關鍵詞，因此不同影片會產生不同內容。",
                question_type="fill-in-the-blank",
                source_time="unknown",
                source_excerpt=snippet,
                starter_code=f'{variable_name} = "___"',
                test_cases=[
                    f'{variable_name} = "{answer}"\nassert {variable_name} == "{answer}"',
                    f'{variable_name} = "{answer}"\nassert isinstance({variable_name}, str)',
                ],
            )
        )

    keyword_source = f"{transcript}\n{outline}".strip()
    for keyword in _extract_keywords(keyword_source, limit=8):
        if len(questions) >= 5:
            break
        if keyword.lower() in used_answers:
            continue
        used_answers.add(keyword.lower())
        variable_name = f"video_keyword_{len(questions) + 1}"
        questions.append(
            schema.QuizQuestion(
                question=f"根據影片主題，補上影片中反覆出現的關鍵字。\n\n```python\n{variable_name} = \"___\"\n```",
                correct_answer=keyword,
                explanation="這題根據影片逐字稿中的高頻關鍵字生成。",
                question_type="fill-in-the-blank",
                source_time="unknown",
                source_excerpt=keyword_source[:120] or "Transcript excerpt unavailable.",
                starter_code=f'{variable_name} = "___"',
                test_cases=[
                    f'{variable_name} = "{keyword}"\nassert {variable_name} == "{keyword}"',
                    f'{variable_name} = "{keyword}"\nassert len({variable_name}) >= 1',
                ],
            )
        )
    return questions


def generate_fallback_questions(title: str, transcript: str = "", outline: str = "") -> list[schema.QuizQuestion]:
    dynamic_questions = _dynamic_fallback_questions(transcript, outline)
    if len(dynamic_questions) >= 5:
        return dynamic_questions[:5]

    defaults = [
        schema.QuizQuestion(
            question=f"根據《{title}》常見的 Python 基礎教學脈絡，補上函式定義需要的關鍵字。\n\n```python\ndef greet(name):\n    ___ f'Hello, {{name}}'\n```",
            correct_answer="return",
            explanation="函式需要使用 return 回傳結果。",
            question_type="fill-in-the-blank",
            source_time="unknown",
            source_excerpt="Fallback question generated because transcript content was unavailable.",
            starter_code="def greet(name):\n    ___ f'Hello, {name}'",
            test_cases=["assert greet('Wei') == 'Hello, Wei'", "assert greet('AHa') == 'Hello, AHa'"],
        ),
        schema.QuizQuestion(
            question="補上列表推導式中的條件，讓函式只保留偶數。\n\n```python\ndef get_even_numbers(nums):\n    return [n for n in nums if ___]\n```",
            correct_answer="n % 2 == 0",
            explanation="這是列表推導式與條件判斷的基礎寫法。",
            question_type="fill-in-the-blank",
            source_time="unknown",
            source_excerpt="Fallback question generated because transcript content was unavailable.",
            starter_code="def get_even_numbers(nums):\n    return [n for n in nums if ___]",
            test_cases=["assert get_even_numbers([1, 2, 3, 4]) == [2, 4]", "assert get_even_numbers([1, 3, 5]) == []"],
        ),
        schema.QuizQuestion(
            question="補上字串去除前後空白的方法。\n\n```python\ndef normalize_text(text):\n    return text.___()\n```",
            correct_answer="strip",
            explanation="這是字串清理的常見方法。",
            question_type="fill-in-the-blank",
            source_time="unknown",
            source_excerpt="Fallback question generated because transcript content was unavailable.",
            starter_code="def normalize_text(text):\n    return text.___()",
            test_cases=["assert normalize_text('  hi  ') == 'hi'", "assert normalize_text('aha') == 'aha'"],
        ),
        schema.QuizQuestion(
            question="補上將字串轉成整數的函式名稱。\n\n```python\ndef parse_age(raw_age):\n    return ___(raw_age)\n```",
            correct_answer="int",
            explanation="這是基本型別轉換。",
            question_type="fill-in-the-blank",
            source_time="unknown",
            source_excerpt="Fallback question generated because transcript content was unavailable.",
            starter_code="def parse_age(raw_age):\n    return ___(raw_age)",
            test_cases=["assert parse_age('12') == 12", "assert parse_age('0') == 0"],
        ),
        schema.QuizQuestion(
            question="補上在迴圈中跳過本次迭代的關鍵字。\n\n```python\nresult = []\nfor n in range(5):\n    if n == 2:\n        ___\n    result.append(n)\n```",
            correct_answer="continue",
            explanation="這是流程控制中的常見關鍵字。",
            question_type="fill-in-the-blank",
            source_time="unknown",
            source_excerpt="Fallback question generated because transcript content was unavailable.",
            starter_code="result = []\nfor n in range(5):\n    if n == 2:\n        ___\n    result.append(n)",
            test_cases=[
                "result = []\nfor n in range(5):\n    if n == 2:\n        continue\n    result.append(n)\nassert result == [0, 1, 3, 4]",
                "result = []\nfor n in range(3):\n    if n == 2:\n        continue\n    result.append(n)\nassert result == [0, 1]",
            ],
        ),
    ]
    needed = max(0, 5 - len(dynamic_questions))
    return dynamic_questions + defaults[:needed]
