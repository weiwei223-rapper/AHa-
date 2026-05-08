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


def generate_text_with_gemini(contents: list[dict], system_instruction: str | None = None, model: str = DEFAULT_GEMINI_MODEL) -> str:
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
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 2048},
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
            raise ValueError(f"Empty text returned from Gemini: {data}")
        return text
    except requests.exceptions.Timeout:
        raise ValueError("Gemini API request timed out")
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Gemini API request failed: {exc}")


def test_gemini_connection(model: str = DEFAULT_GEMINI_MODEL) -> dict:
    text = generate_text_with_gemini(
        contents=[{"role": "user", "parts": [{"text": "Reply with exactly: GEMINI_OK"}]}], 
        model=model
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


def _format_questions_context(questions: list[dict]) -> str:
    blocks: list[str] = []
    for index, question in enumerate(questions[:8], start=1):
        prompt = str(question.get("question") or "").strip()
        answer = str(question.get("reference_answer") or "").strip()
        learner_answer = str(question.get("answer_record") or "").strip()
        accuracy = question.get("accuracy")
        block = f"Question {index}: {prompt}\nReference answer: {answer}"
        if learner_answer:
            block += f"\nLearner answer: {learner_answer}"
        if accuracy is not None:
            block += f"\nAccuracy: {accuracy}"
        blocks.append(block)
    return "\n\n".join(blocks)


def build_selected_video_context(video: dict) -> str:
    title = str(video.get("title") or "Untitled video").strip()
    link = str(video.get("video_link") or "").strip()
    outline = str(video.get("outline") or "").strip()
    transcript = str(video.get("transcript") or "").strip()
    transcript_source = str(video.get("transcript_source") or "").strip() or "unavailable"
    retrieved_chunks = video.get("retrieved_chunks") or []
    questions = video.get("questions") or []

    chunk_text = "\n\n".join(
        f"[Chunk {chunk.get('index')}] {str(chunk.get('content') or '').strip()}"
        for chunk in retrieved_chunks[:5]
        if str(chunk.get("content") or "").strip()
    )
    if not chunk_text and transcript:
        chunk_text = transcript[:MAX_CHAT_TRANSCRIPT_CHARS]

    question_text = _format_questions_context(questions if isinstance(questions, list) else [])
    return (
        f"Selected video\n"
        f"Title: {title}\n"
        f"Link: {link}\n"
        f"Transcript source: {transcript_source}\n\n"
        f"Video outline:\n{outline or 'No outline saved.'}\n\n"
        f"Relevant transcript evidence:\n{chunk_text or 'Transcript evidence unavailable.'}\n\n"
        f"Generated quiz questions for this video:\n{question_text or 'No generated quiz questions saved yet.'}"
    )


def build_video_context(videos: list[dict] | dict) -> str:
    if isinstance(videos, dict):
        return build_selected_video_context(videos)

    blocks: list[str] = []
    for index, video in enumerate(videos[:MAX_CONTEXT_VIDEOS], start=1):
        title = str(video.get("title") or "Untitled video").strip()
        link = str(video.get("video_link") or "").strip()
        outline = str(video.get("outline") or "").strip()
        transcript = str(video.get("transcript") or "").strip() or fetch_video_transcript(link, max_chars=MAX_CHAT_TRANSCRIPT_CHARS)
        if transcript:
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nOutline:\n{outline}\nTranscript excerpt:\n{transcript}")
        else:
            blocks.append(f"Video {index}\nTitle: {title}\nLink: {link}\nOutline:\n{outline}\nTranscript excerpt unavailable.")
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


def generate_transcript_fallback_reply(message: str, videos: list[dict] | dict | None = None) -> str:
    if isinstance(videos, dict):
        title = str(videos.get("title") or "未命名影片").strip()
        transcript = str(videos.get("transcript") or "").strip()
        outline = str(videos.get("outline") or "").strip()
        questions = videos.get("questions") if isinstance(videos.get("questions"), list) else []
        question_text = _format_questions_context(questions)
        source_text = transcript or outline
        if not source_text and not question_text:
            return f"我目前沒有《{title}》的逐字稿、摘要或題目資料，所以沒辦法可靠地根據影片內容回答。"
        summary = _summarize_transcript(source_text)
        if question_text and ("題" in message or "答案" in message or "解析" in message):
            return f"根據《{title}》已儲存的題目資料：\n{question_text[:1000]}"
        return f"根據《{title}》目前可取得的影片內容，重點是：{summary}".strip()

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


def generate_chat_reply(message: str, history: list[dict], videos: list[dict] | dict | None = None) -> str:
    video_context = build_video_context(videos or [])
    system_prompt = (
        "You are the AHa study assistant. "
        "Always answer in Traditional Chinese. "
        "Answer according to the selected video's content and its generated quiz questions. "
        "Use the transcript evidence, outline, and quiz reference answers as the primary sources. "
        "When explaining a quiz question, compare the user's question with the saved question and reference answer. "
        "If the context is insufficient, say clearly that the current video data does not contain enough evidence. "
        "Do not copy long passages from transcripts directly. "
        "Keep answers clear, concise, and useful for learning."
    )
    
    full_system_instruction = system_prompt
    if video_context:
        full_system_instruction += f"\n\nUploaded video context:\n{video_context}"

    contents = []
    for item in history:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()
        if content:
            # Gemini uses 'model' instead of 'assistant'
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    
    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    
    # Optional: ensure alternating user/model roles if required by Gemini
    # (Though usually it handles it if they alternate)
    
    for model in [DEFAULT_GEMINI_MODEL, "gemini-1.5-flash"]:
        try:
            reply = generate_text_with_gemini(contents, system_instruction=full_system_instruction, model=model)
            if reply and len(reply.strip()) >= 2:
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


def _answer_for_template(template: question_bank.QuestionTemplate, keyword_pool: list[str]) -> str:
    starter = template.starter_code
    if ".___()" in starter:
        return "strip"
    if "return ___(" in starter:
        return "int"
    if "return [n for n in nums if ___]" in starter:
        return "n % 2 == 0"
    if "___ f'Hello, {name}'" in starter or '___ f"Hello, {name}"' in starter:
        return "return"
    if "if ___ else" in starter:
        return "score >= 60"
    if "if value == target:\n        ___" in starter:
        return "continue"
    return keyword_pool[0] if keyword_pool else "value"


def generate_fallback_questions(
    title: str,
    transcript: str = "",
    outline: str = "",
    templates: list[question_bank.QuestionTemplate] | None = None,
) -> list[schema.QuizQuestion]:
    snippets = _extract_transcript_snippets(transcript, limit=5) or _extract_transcript_snippets(outline, limit=5)
    keyword_pool = _extract_keywords(f"{transcript}\n{outline}", limit=10)
    questions: list[schema.QuizQuestion] = []
    used_starters: set[str] = set()
    used_answers: set[str] = set()

    for index, snippet in enumerate(snippets, start=1):
        if len(questions) >= 5:
            break
        answer = _pick_answer_from_snippet(snippet)
        if answer.lower() in used_answers:
            continue
        used_answers.add(answer.lower())
        variable_name = f"video_fact_{index}"
        questions.append(
            schema.QuizQuestion(
                question=f"根據影片內容，補上最符合這段描述的關鍵字。\n\n```python\n{variable_name} = \"___\"\n```",
                correct_answer=answer,
                explanation="這題直接根據影片片段抽取關鍵詞，所以不同影片會得到不同答案。",
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

    for template in templates or []:
        if len(questions) >= 5:
            break
        starter = template.starter_code.strip()
        if not starter or starter in used_starters:
            continue
        used_starters.add(starter)
        answer = _answer_for_template(template, keyword_pool)
        if answer.lower() in used_answers:
            continue
        used_answers.add(answer.lower())
        starter_code = starter.replace(answer, "___", 1) if answer in starter else starter
        questions.append(
            schema.QuizQuestion(
                question=(
                    f"請依照影片內容，使用 LeetCode 題型骨架完成這題填空。\n\n```python\n{starter_code}\n```"
                ),
                correct_answer=answer,
                explanation=f"這題套用了 LeetCode 模板 `{template.title}` 的程式骨架，但答案仍依影片內容或影片關鍵詞生成。",
                question_type="fill-in-the-blank",
                source_time="unknown",
                source_excerpt=(snippets[0] if snippets else outline[:120] or title),
                starter_code=starter_code,
                test_cases=template.test_case_examples[:2] or ["assert True", "assert 1 == 1"],
            )
        )

    return questions[:5]
