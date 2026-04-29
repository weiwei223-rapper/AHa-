from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

try:
    from . import ai_analyzer, schema
except ImportError:
    import ai_analyzer
    import schema

try:
    from langchain_community.document_loaders import YoutubeLoader
except ImportError:
    try:
        from langchain.document_loaders import YoutubeLoader  # type: ignore
    except ImportError:
        YoutubeLoader = None  # type: ignore

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None  # type: ignore


TRANSCRIPT_PREVIEW_CHARS = 1000
OUTLINE_CHUNK_SIZE = 4000
OUTLINE_CHUNK_OVERLAP = 400
RETRIEVAL_CHUNK_SIZE = 900
RETRIEVAL_CHUNK_OVERLAP = 180
RETRIEVAL_TOP_K = 4

MBPP_FEW_SHOT_EXAMPLES = [
    {
        "topic": "list filtering",
        "question": "撰寫函式，回傳串列中所有大於 0 的整數總和。",
        "starter_code": "def sum_positive(numbers):\n    pass",
        "test_cases": [
            "assert sum_positive([1, -2, 3, 4]) == 8",
            "assert sum_positive([-5, -1]) == 0",
        ],
    },
    {
        "topic": "string processing",
        "question": "撰寫函式，移除字串中的所有空白字元。",
        "starter_code": "def remove_spaces(text):\n    pass",
        "test_cases": [
            "assert remove_spaces('a b c') == 'abc'",
            "assert remove_spaces(' hello ') == 'hello'",
        ],
    },
    {
        "topic": "loop and counting",
        "question": "撰寫函式，計算串列中偶數的個數。",
        "starter_code": "def count_even(numbers):\n    pass",
        "test_cases": [
            "assert count_even([1, 2, 3, 4]) == 2",
            "assert count_even([1, 3, 5]) == 0",
        ],
    },
]


@dataclass
class TranscriptResult:
    transcript: str
    source: str


@dataclass
class RetrievalChunk:
    index: int
    content: str
    score: float


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_bullets(markdown: str) -> list[str]:
    topics: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            topic = stripped[2:].strip()
            if topic:
                topics.append(topic)
    return topics[:8]


def _simple_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end].strip())
        if end >= text_length:
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if RecursiveCharacterTextSplitter is None:
        return _simple_chunks(text, chunk_size, overlap)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_text(text)


def _call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 1800) -> str:
    return ai_analyzer.generate_text_with_gemini(
        [{"role": "user", "parts": [{"text": prompt}]}]
    )


def load_transcript(video_link: str) -> TranscriptResult:
    if YoutubeLoader is not None:
        try:
            loader = YoutubeLoader.from_youtube_url(
                video_link,
                add_video_info=False,
                language=["zh-TW", "zh-Hant", "zh-CN", "zh", "en"],
            )
            docs = loader.load()
            transcript = _normalize_whitespace("\n".join(doc.page_content for doc in docs))
            if len(transcript) >= 200:
                return TranscriptResult(transcript=transcript, source="langchain-youtube-loader")
        except Exception as exc:
            print(f"LangChain YouTubeLoader unavailable for {video_link}: {exc}")

    transcript = ai_analyzer.fetch_video_transcript(video_link)
    if transcript:
        source = "whisper-fallback" if "Transcript unavailable" not in transcript else "fallback"
        return TranscriptResult(transcript=transcript, source=source)

    return TranscriptResult(transcript="", source="unavailable")


def generate_outline(transcript: str, title: str) -> str:
    if not transcript.strip():
        return "- 無法取得逐字稿\n- 目前無法建立課程大綱"

    chunks = _split_text(transcript, OUTLINE_CHUNK_SIZE, OUTLINE_CHUNK_OVERLAP)
    chunk_summaries: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        prompt = f"""
你是課程內容分析助手。請閱讀以下影片逐字稿片段，輸出 3-5 個重點條列。
要求：
- 使用繁體中文
- 每點一句
- 聚焦教學重點、概念、程式技巧與範例

影片標題：{title}
片段編號：{index}/{len(chunks)}
逐字稿片段：
{chunk}
"""
        summary = _call_llm(prompt, temperature=0.2, max_tokens=600)
        chunk_summaries.append(summary)

    merged_prompt = f"""
你是課綱整理助手。請依據以下分段摘要，整理成一份結構清楚的課程大綱。
要求：
- 使用繁體中文
- 以 Markdown 條列
- 先列出 4-8 個主要教學重點
- 每個重點下可有 1-2 個子點
- 僅輸出大綱，不要額外說明

影片標題：{title}

分段摘要：
{chr(10).join(chunk_summaries)}
"""
    return _call_llm(merged_prompt, temperature=0.2, max_tokens=900)


def build_retrieval_index(transcript: str) -> tuple[list[str], str]:
    chunks = _split_text(transcript, RETRIEVAL_CHUNK_SIZE, RETRIEVAL_CHUNK_OVERLAP)
    return chunks, "memory-keyword"


def retrieve_chunks(query: str, transcript: str, top_k: int = RETRIEVAL_TOP_K) -> tuple[list[RetrievalChunk], str]:
    chunks, backend = build_retrieval_index(transcript)
    if not chunks:
        return [], backend

    lowered_terms = set(re.findall(r"\w+", query.lower()))
    fallback_scores: list[RetrievalChunk] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_terms = set(re.findall(r"\w+", chunk.lower()))
        score = float(len(lowered_terms & chunk_terms))
        fallback_scores.append(RetrievalChunk(index=index, content=chunk, score=score))
    fallback_scores.sort(key=lambda item: item.score, reverse=True)
    return fallback_scores[:top_k], "memory-keyword"


def analyze_video(video_id: int, title: str, video_link: str) -> schema.VideoAnalysisResponse:
    transcript_result = load_transcript(video_link)
    outline = generate_outline(transcript_result.transcript, title)
    topics = _parse_bullets(outline)
    retrieval_query = " ".join(topics[:3]) or title
    chunks, backend = retrieve_chunks(retrieval_query, transcript_result.transcript)

    return schema.VideoAnalysisResponse(
        video_id=video_id,
        video_title=title,
        transcript_source=transcript_result.source,
        transcript_excerpt=transcript_result.transcript[:TRANSCRIPT_PREVIEW_CHARS],
        outline_markdown=outline,
        key_topics=topics,
        retrieved_chunks=[
            schema.TranscriptChunk(index=chunk.index, content=chunk.content, score=round(chunk.score, 4))
            for chunk in chunks
        ],
        vector_backend=backend,
        generated_at=datetime.utcnow(),
    )


def _extract_json_array(payload: str) -> list[dict[str, Any]]:
    start = payload.find("[")
    end = payload.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in model response")
    data = json.loads(payload[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("Model response is not a JSON array")
    return data


def generate_quiz(video_id: int, title: str, video_link: str) -> schema.QuizResponse:
    analysis = analyze_video(video_id, title, video_link)
    retrieved_context = "\n\n".join(
        f"[Chunk {chunk.index}] {chunk.content}" for chunk in analysis.retrieved_chunks
    )
    few_shot_examples = json.dumps(MBPP_FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)

    prompt = f"""
你是 Python 程式填空題設計助手。請根據影片教學內容，產生 5 題「程式填空題」。
每題應包含一段帶有缺漏（使用 `___` 表示）的程式碼，並要求使用者填入正確的片段。

課程標題：{title}
課程大綱：
{analysis.outline_markdown}

檢索到的原始字幕片段：
{retrieved_context}

輸出要求：
1. 使用繁體中文。
2. 回傳 JSON array，固定 5 題。
3. 題目必須「完全運用影片有提到的語法、概念或邏輯」。
4. 每題包含以下欄位：
   - question: 題目敘述加上包含 `___` 的程式碼區塊
   - correct_answer: 填入 `___` 處的正確程式碼片段
   - explanation: 說明該程式碼的作用，並強調這是在影片哪個部分提到的
   - starter_code: 給前端編輯器的完整程式碼（包含 `___`），方便使用者複製或修改
   - test_cases: 2 到 4 筆 Python assert 測試（選填）
5. 僅輸出 JSON，不要加 markdown。

範例格式：
{{
  "question": "在影片中我們學到如何過濾正數，請填補以下缺漏：\\n\\n```python\\ndef filter_pos(nums):\\n    return [x for x in nums if ___]\\n```",
  "correct_answer": "x > 0",
  "explanation": "影片中提到使用列表推導式配合條件判斷來過濾元素，這裡應判斷 x 是否大於 0。",
  "starter_code": "def filter_pos(nums):\\n    return [x for x in nums if ___]"
}}
"""

    try:
        payload = _call_llm(prompt, temperature=0.35, max_tokens=2200)
        raw_questions = _extract_json_array(payload)
        questions = [
            schema.QuizQuestion(
                question=item.get("question", ""),
                correct_answer=str(item.get("correct_answer", "")),
                explanation=item.get("explanation"),
                starter_code=item.get("starter_code"),
                test_cases=item.get("test_cases") or [],
            )
            for item in raw_questions
        ]
        return schema.QuizResponse(
            video_id=video_id,
            video_title=title,
            quiz_type="rag-fill-in-blank",
            questions=questions,
        )
    except Exception as exc:
        print(f"Quiz generation fallback for {title}: {exc}")
        fallback_questions = ai_analyzer.generate_fallback_questions(title)
        enriched = [
            schema.QuizQuestion(
                question=item.question,
                correct_answer=item.correct_answer,
                explanation=item.explanation,
                starter_code=item.starter_code,
                test_cases=MBPP_FEW_SHOT_EXAMPLES[index % len(MBPP_FEW_SHOT_EXAMPLES)]["test_cases"],
            )
            for index, item in enumerate(fallback_questions)
        ]
        return schema.QuizResponse(
            video_id=video_id,
            video_title=title,
            quiz_type="fallback-fill-in-blank",
            questions=enriched,
        )
