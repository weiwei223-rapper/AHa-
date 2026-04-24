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
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TRANSCRIPT_LANGUAGES = ("zh-TW", "zh-Hant", "zh-CN", "zh", "en")
MAX_TRANSCRIPT_CHARS = 12000
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
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("AI_API_KEY not found in environment variables")
    return api_key


def generate_text_with_gemini(contents: list[dict], model: str = DEFAULT_GEMINI_MODEL) -> str:
    api_key = init_gemini()
    response = requests.post(
        GEMINI_API_URL.format(model=model),
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": contents,
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 2048,
            },
        },
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"No candidates returned from Gemini: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ValueError(f"Empty text returned from Gemini: {data}")
    return text


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
    if not transcript:
        return
    path = _get_cached_transcript_path(video_id)
    path.write_text(transcript, encoding="utf-8")


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

        # yt-dlp may adjust extension after download.
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
        transcript = fetch_video_transcript(link)
        if transcript:
            blocks.append(
                f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt:\n{transcript}"
            )
        else:
            blocks.append(
                f"Video {index}\nTitle: {title}\nLink: {link}\nTranscript excerpt unavailable."
            )
    return "\n\n".join(blocks)


def _split_sentences(text: str) -> list[str]:
    normalized = text.replace("[Music]", " ").replace("[Applause]", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _pick_relevant_video(message: str, videos: list[dict]) -> dict | None:
    prompt = message.lower().strip()
    for video in videos:
        title = str(video.get("title") or "").lower()
        if title and title in prompt:
            return video

    for video in videos:
        transcript = fetch_video_transcript(str(video.get("video_link") or ""), max_chars=300)
        if transcript:
            return video

    return videos[0] if videos else None


def _extract_keywords(text: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def _infer_topics(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    topics: list[str] = []

    if "python" in lower or "interpreter" in lower:
        topics.append("Python 入門與執行環境")
    if "pycharm" in lower or "idle" in lower or "ide" in lower:
        topics.append("如何選擇與開啟開發工具")
    if "binary" in lower or "zeros and ones" in lower or "computer understands" in lower:
        topics.append("為什麼需要程式語言與電腦溝通")
    if "assistant" in lower or "siri" in lower or "alarm" in lower:
        topics.append("日常生活中的電腦指令與自動化例子")

    if not topics and keywords:
        topics.append(f"重點可能圍繞 {', '.join(keywords[:3])}")

    return topics[:3]


def _summarize_transcript(transcript: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", " ", transcript)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "目前沒有足夠的字幕內容可整理。"

    keywords = _extract_keywords(cleaned)
    topics = _infer_topics(cleaned, keywords)

    summary_parts = []
    if topics:
        summary_parts.append(f"這支影片主要在介紹：{'、'.join(topics)}。")
    if keywords:
        summary_parts.append(f"字幕中的高頻重點包括：{', '.join(keywords)}。")
    return "\n".join(summary_parts) or "這支影片主要是在說明程式設計的入門概念。"


def _outline_from_transcript(transcript: str) -> list[str]:
    keywords = _extract_keywords(transcript, limit=8)
    topics = _infer_topics(transcript, keywords)
    outline = [f"說明 {topic}" for topic in topics]
    if "python" in transcript.lower():
        outline.append("帶入 Python 學習情境，說明如何開始寫程式")
    if "computer" in transcript.lower():
        outline.append("用電腦與人類語言的差異，解釋程式語言存在的必要性")
    return outline[:3]


def _answer_from_transcript(question: str, title: str, transcript: str) -> str:
    normalized_question = question.strip().lower()
    summary = _summarize_transcript(transcript)
    outline = _outline_from_transcript(transcript)

    if any(token in normalized_question for token in ["重點", "摘要", "整理", "大綱"]):
        lines = [f"根據《{title}》的字幕內容，我整理出這些重點："]
        lines.extend(f"{idx}. {item}" for idx, item in enumerate(outline or [summary], start=1))
        return "\n".join(lines)

    if any(token in normalized_question for token in ["內容", "講什麼", "在講什麼", "介紹什麼"]):
        return f"根據《{title}》的字幕內容，{summary}"

    return (
        f"我根據《{title}》的字幕內容回答你的問題。\n"
        f"{summary}\n"
        "如果你要更精準，我可以進一步幫你整理重點、列大綱，或直接根據這支影片出題。"
    )


def generate_transcript_fallback_reply(message: str, videos: list[dict] | None = None) -> str:
    available_videos = videos or []
    selected = _pick_relevant_video(message, available_videos)
    if not selected:
        return (
            "目前 AI 服務暫時忙碌，而且沒有可用的影片內容可供分析。\n"
            "請先上傳影片，或在問題中指出你要詢問哪一支影片。"
        )

    title = str(selected.get("title") or "未命名影片").strip()
    link = str(selected.get("video_link") or "").strip()
    transcript = fetch_video_transcript(link, max_chars=2200)

    if not transcript:
        return (
            f"目前 AI 服務暫時忙碌，而且《{title}》這支影片目前抓不到字幕內容。\n"
            "請確認影片字幕是公開可讀取的，或改用其他有字幕的 YouTube 影片。"
        )

    return _answer_from_transcript(message, title, transcript)


def generate_chat_reply(message: str, history: list[dict], videos: list[dict] | None = None) -> str:
    video_context = build_video_context(videos or [])
    system_prompt = (
        "You are the AHa study assistant. "
        "Answer in Traditional Chinese. "
        "If uploaded video transcript context is available, prioritize it. "
        "Directly answer the user's question instead of dumping transcript text."
    )

    contents = [{"role": "user", "parts": [{"text": system_prompt}]}]

    if video_context:
        contents.append(
            {"role": "user", "parts": [{"text": f"Uploaded video context:\n{video_context}"}]}
        )

    for item in history:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )

    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    return generate_text_with_gemini(contents)


def analyze_video_content_with_ai(video_link: str, title: str) -> list[schema.QuizQuestion]:
    transcript = fetch_video_transcript(video_link)
    prompt = f"""
Based on the following video information, generate 5 multiple-choice quiz questions in Traditional Chinese.

Video Title: {title}
Video Link: {video_link}
Transcript Excerpt:
{transcript or "Transcript unavailable."}

Requirements:
1. Create 5 quiz questions that test understanding of the actual video content.
2. Each question should have 4 multiple-choice options.
3. Include the index (0-3) of the correct answer.
4. If transcript is unavailable, create broader questions based on the title only.
5. Return ONLY a valid JSON array with no additional text.
"""
    try:
        response_text = generate_text_with_gemini(
            [{"role": "user", "parts": [{"text": prompt}]}]
        )
        quiz_data = parse_ai_response(response_text)
        return [
            schema.QuizQuestion(
                question=item.get("question", ""),
                options=item.get("options", []),
                correct_answer=item.get("correct_answer", 0),
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
        if not all(key in item for key in ["question", "options", "correct_answer"]):
            raise ValueError("Missing required fields in question")
        if len(item["options"]) != 4:
            raise ValueError("Each question must have exactly 4 options")
    return quiz_data


def generate_fallback_questions(title: str) -> list[schema.QuizQuestion]:
    return [
        schema.QuizQuestion(
            question=f"《{title}》最可能聚焦在哪一類主題？",
            options=["核心概念介紹", "天氣預報", "體育新聞", "旅遊訂房"],
            correct_answer=0,
        ),
        schema.QuizQuestion(
            question=f"學習《{title}》時，最應該先注意哪一項？",
            options=["影片的主要名詞與概念", "留言區抽獎資訊", "背景音樂歌詞", "影片封面顏色"],
            correct_answer=0,
        ),
        schema.QuizQuestion(
            question=f"如果你想用《{title}》做複習，哪個方法最有效？",
            options=["整理重點並記錄問題", "只看縮圖", "跳過內容直接猜答案", "只記上傳時間"],
            correct_answer=0,
        ),
        schema.QuizQuestion(
            question=f"觀看《{title}》後，最適合做的下一步是什麼？",
            options=["比對影片重點與自己的理解", "完全不做筆記", "只看廣告內容", "忽略影片主題"],
            correct_answer=0,
        ),
        schema.QuizQuestion(
            question="若影片字幕不可用，系統生成題目的依據主要會是什麼？",
            options=["影片標題與連結資訊", "你的電腦時間", "瀏覽器主題色", "隨機網頁內容"],
            correct_answer=0,
        ),
    ]
