from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from . import ai_analyzer, question_bank, schema
except ImportError:
    import ai_analyzer
    import question_bank
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


def _call_llm(prompt: str) -> str:
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
        return TranscriptResult(transcript=transcript, source="youtube-transcript-or-whisper")

    return TranscriptResult(transcript="", source="unavailable")


def generate_outline(transcript: str, title: str) -> str:
    if not transcript.strip():
        return "- 無法取得影片逐字稿\n- 目前不能生成可靠的影片摘要"

    chunks = _split_text(transcript, OUTLINE_CHUNK_SIZE, OUTLINE_CHUNK_OVERLAP)
    chunk_summaries: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        prompt = f"""
請用繁體中文整理以下影片逐字稿片段。

要求：
1. 用 3 到 5 點條列。
2. 每點聚焦在這段內容的具體重點。
3. 不要補外部知識。
4. 優先保留可以轉成程式題目的概念、流程或關鍵詞。

影片標題：{title}
片段：{index}/{len(chunks)}

逐字稿：
{chunk}
"""
        chunk_summaries.append(_call_llm(prompt))

    merged_prompt = f"""
請把以下分段摘要整合成一份影片重點整理，使用繁體中文 Markdown 條列。

要求：
1. 產出 4 到 8 點。
2. 每點精簡明確。
3. 只根據提供內容整理。
4. 優先保留可出題的事實、步驟、概念與結論。

影片標題：{title}

分段摘要：
{chr(10).join(chunk_summaries)}
"""
    return _call_llm(merged_prompt)


def build_retrieval_index(transcript: str) -> tuple[list[str], str]:
    chunks = _split_text(transcript, RETRIEVAL_CHUNK_SIZE, RETRIEVAL_CHUNK_OVERLAP)
    return chunks, "memory-keyword"


def retrieve_chunks(query: str, transcript: str, top_k: int = RETRIEVAL_TOP_K) -> tuple[list[RetrievalChunk], str]:
    chunks, backend = build_retrieval_index(transcript)
    if not chunks:
        return [], backend

    lowered_terms = set(re.findall(r"\w+", query.lower()))
    scores: list[RetrievalChunk] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_terms = set(re.findall(r"\w+", chunk.lower()))
        score = float(len(lowered_terms & chunk_terms))
        scores.append(RetrievalChunk(index=index, content=chunk, score=score))
    scores.sort(key=lambda item: item.score, reverse=True)
    return scores[:top_k], backend


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
        print(f"[DEBUG] JSON extraction failed: start={start}, end={end}")
        print(f"[DEBUG] Payload (first 300 chars): {payload[:300]}")
        raise ValueError("No JSON array found in model response")
    try:
        data = json.loads(payload[start:end + 1])
        if not isinstance(data, list):
            raise ValueError("Model response is not a JSON array")
        print(f"[DEBUG] Successfully extracted {len(data)} items from JSON")
        return data
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON parse error: {e}")
        print(f"[DEBUG] Attempted to parse: {payload[start:min(end+1, start+500)]}")
        raise ValueError(f"Failed to parse JSON array: {e}")


def _normalize_test_cases(item: dict[str, Any]) -> list[str]:
    raw_cases = item.get("test_cases")
    if isinstance(raw_cases, list):
        return [
            str(case).strip()
            for case in raw_cases
            if str(case).strip().startswith("assert")
        ]

    if isinstance(raw_cases, str):
        lines = [line.strip() for line in re.split(r"\r?\n", raw_cases) if line.strip()]
        return [line for line in lines if line.startswith("assert")]

    single_case_keys = ["assert_statement", "assert", "test_case"]
    cases: list[str] = []
    for key in single_case_keys:
        value = item.get(key)
        if value:
            text = str(value).strip()
            if text:
                cases.append(text)
    return cases


def _build_fallback_test_cases(starter_code: str, correct_answer: str) -> list[str]:
    """Build test cases that verify the correct answer when replacing ___ in starter_code."""
    if not starter_code or "___" not in starter_code:
        return []
    
    # Generate test case code by replacing ___ with correct answer
    test_code = starter_code.replace("___", repr(correct_answer) if isinstance(correct_answer, str) else str(correct_answer))
    
    # Try to extract variable name or function name for assertion
    assignment_match = re.search(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=", test_code, re.MULTILINE)
    function_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", test_code, re.MULTILINE)
    
    test_cases: list[str] = []
    
    if assignment_match:
        variable_name = assignment_match.group(1)
        test_cases.append(f"{test_code}\nassert {variable_name} is not None")
    elif function_match:
        function_name = function_match.group(1)
        test_cases.append(f"{test_code}\nassert callable({function_name})")
    else:
        # If no clear structure, just include the code as is with a basic assertion
        test_cases.append(f"{test_code}\nassert True")
    
    # Add a second test case if possible
    if assignment_match:
        variable_name = assignment_match.group(1)
        test_cases.append(f"{test_code}\nassert len(str({variable_name})) > 0")
    
    return test_cases[:2] if test_cases else []


def _normalize_question(item: dict[str, Any]) -> schema.QuizQuestion:
    question = str(item.get("question") or item.get("question_text") or item.get("prompt") or "").strip()
    correct_answer = str(item.get("correct_answer") or item.get("answer") or "").strip()
    starter_code = str(item.get("starter_code") or item.get("code") or item.get("snippet") or "").strip()
    source_excerpt = str(item.get("source_excerpt") or item.get("quote") or "").strip() or None
    explanation = str(item.get("explanation") or "").strip() or None
    source_time = str(item.get("source_time") or "unknown").strip() or "unknown"
    question_type = str(item.get("question_type") or "fill-in-the-blank").strip() or "fill-in-the-blank"
    test_cases = _normalize_test_cases(item)

    # Debug output
    print(f"[NORMALIZE] Q: q_len={len(question)}, ans_len={len(correct_answer)}, code_len={len(starter_code)}, type={question_type}")
    
    if question_type == "fill-in-the-blank" and starter_code and "___" not in starter_code and correct_answer:
        print(f"[NORMALIZE] Replacing {repr(correct_answer)} with ___ in starter_code")
        starter_code = starter_code.replace(correct_answer, "___", 1)

    if not explanation and source_excerpt:
        explanation = f"這題根據影片內容出題：{source_excerpt}"

    if not test_cases and question_type == "fill-in-the-blank" and starter_code and correct_answer:
        print(f"[NORMALIZE] Generating fallback test cases")
        test_cases = _build_fallback_test_cases(starter_code, correct_answer)

    print(f"[NORMALIZE] Result: blanks={'___' in (starter_code or '')}, tests={len(test_cases)}")

    return schema.QuizQuestion(
        question=question,
        correct_answer=correct_answer,
        explanation=explanation,
        question_type=question_type,
        source_time=source_time,
        source_excerpt=source_excerpt,
        starter_code=starter_code or None,
        test_cases=test_cases,
    )


def generate_quiz(video_id: int, title: str, video_link: str, outline: str | None = None) -> schema.QuizResponse:
    analysis = analyze_video(video_id, title, video_link)
    video_outline = (outline or analysis.outline_markdown or "").strip()
    retrieved_context = "\n\n".join(
        f"[Chunk {chunk.index}] {chunk.content}" for chunk in analysis.retrieved_chunks
    )
    reference_templates = question_bank.retrieve_templates(
        title,
        analysis.key_topics,
        analysis.transcript_excerpt,
    )
    template_context = question_bank.format_templates_for_prompt(reference_templates)

    prompt = f"""
你是一位專業的 Python 教學設計師。
請根據提供的影片內容，生成 5 題高品質的「填空式」程式練習題。

這些題目必須：
1. **真實反映影片內容**：題目場景與教學重點必須來自影片逐字稿與大綱。
2. **合理的難度與教學價值**：如果影片是基礎教學，請出基礎題；如果是進階，則出進階題。
3. **優質的程式碼範本**：`starter_code` 應包含具備教學價值的 Python 片段，將關鍵部分置換為 `___ (1) ___` 等。
4. **教學引導**：`explanation` 應詳細說明為何答案是該選項，並連結到影片中的具體概念。

影片標題：
{title}

影片重點摘要：
{video_outline}

影片內容證據（逐字稿片段）：
{retrieved_context}

參考程式模式（僅供結構參考，若難度不符請自行調整）：
{template_context}

要求細節：
1. 使用繁體中文編寫題目文字與解析。
2. 每題 `question` 必須包含題目名稱、描述以及完整的程式碼骨架（含編號填空點）。
3. 填空點必須標記為 ___ (1) ___ , ___ (2) ___ 等。
4. 在程式碼區塊之後，請逐行列表每個填空的答案："* (1) 填空內容：答案1" 等。
5. 題目內容必須源自影片，而非外部知識。
6. `correct_answer` 應為所有填空答案的組合，以 | 分隔，例如 "答案1|答案2"。
7. `starter_code` 應為包含填空點標記的程式碼骨架，與 `question` 中的相同。
8. `test_cases` 必須包含 4 到 8 個 `assert` 風格的測試案例，用來驗證所有填空點。
9. `question_type` 必須為 `fill-in-the-blank`。
10. `source_excerpt` 必須引用影片中最相關的原話。
11. 至少 3 題應明顯遵循所提供的參考模板之一。
12. 請直接回傳純 JSON 陣列，不要添加任何 Markdown 標籤或額外文字。

回傳格式：
[
  {{
    "question": "完整的題目描述（包含程式碼框架和填空點）",
    "correct_answer": "答案1|答案2|答案3",
    "starter_code": "包含 ___ (1) ___ 標記的程式碼框架",
    "explanation": "簡短解析",
    "question_type": "fill-in-the-blank",
    "source_time": "unknown",
    "source_excerpt": "影片相關內容片段",
    "test_cases": ["assert ...", "assert ...", "assert ..."]
  }}
]
"""

    try:
        print(f"\n=== Generating quiz for video: {title} ===")
        print(f"Outline length: {len(video_outline)} chars")
        print(f"Retrieved chunks: {len(analysis.retrieved_chunks)}")
        print(f"Reference templates: {len(reference_templates)}")
        
        payload = _call_llm(prompt)
        print(f"LLM Response length: {len(payload)} chars")
        print(f"LLM Response (first 500 chars): {payload[:500]}...")
        
        raw_questions = _extract_json_array(payload)
        print(f"Extracted {len(raw_questions)} raw questions")
        
        questions = [_normalize_question(item) for item in raw_questions]
        print(f"Normalized {len(questions)} questions")
        
        for idx, q in enumerate(questions, 1):
            has_blanks = "___" in (q.starter_code or "")
            test_count = len(q.test_cases)
            print(f"  Q{idx}: blanks={has_blanks}, tests={test_count}, correct_answer_len={len(q.correct_answer)}")

        valid_questions = [
            question
            for question in questions
            if question.question
            and question.correct_answer
            and question.starter_code
            and "___" in (question.starter_code or "")
            and len(question.test_cases) >= 2
        ]
        print(f"Valid questions: {len(valid_questions)}/5")
        
        if len(valid_questions) != 5:
            raise ValueError(f"Model did not return 5 valid fill-in-the-blank questions (got {len(valid_questions)})")

        print(f"✓ Quiz generated successfully")
        return schema.QuizResponse(
            video_id=video_id,
            video_title=title,
            quiz_type="template-rag-fill-in-blank",
            questions=valid_questions,
        )
    except Exception as exc:
        import traceback
        print(f"\n✗ Quiz generation failed for {title}")
        print(f"Error: {exc}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"Falling back to simple fallback questions...\n")
        
        fallback_questions = ai_analyzer.generate_fallback_questions(
            title,
            transcript=analysis.transcript_excerpt,
            outline=analysis.outline_markdown,
        )
        return schema.QuizResponse(
            video_id=video_id,
            video_title=title,
            quiz_type="fallback-video-fill-in-blank",
            questions=fallback_questions,
        )
