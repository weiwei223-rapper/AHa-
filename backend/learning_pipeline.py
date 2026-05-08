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
You are AHa!'s Python exercise designer for learning videos.
Generate exactly 5 Python fill-in-the-blank coding exercises based on the video content.

Each exercise should have:
- A clear problem title (e.g., "經典迴圈數字處理 (Palindrome Number)")
- A detailed problem description with learning context
- A code skeleton with 1-3 specific blank points marked as ___ (1) ___ , ___ (2) ___, etc.
- Each blank point has a clear answer

Example format:
"第 1 題：找因數

請完成一個函數來找出某個整數的所有因數。

參考概念：for 迴圈、取餘數 (%)

def find_factors(n):
    factors = []
    for i in range(1, n + 1):
        if ___ (1) ___:
            factors.append(i)
    return ___ (2) ___

* (1) 填空內容：n % i == 0
* (2) 填空內容：factors"

You must use the video content as the semantic source, and use the retrieved LeetCode/TQC templates as style and structure references.

Video title:
{title}

Video outline:
{video_outline}

Transcript evidence:
{retrieved_context}

Retrieved LeetCode/TQC templates:
{template_context}

Requirements:
1. Use Traditional Chinese for question text and explanation.
2. Each `question` must contain the problem title, description, and full code skeleton with numbered blank points.
3. The blank points must be marked as ___ (1) ___, ___ (2) ___, etc.
4. After the code block, list each answer on a new line: "* (1) 填空內容：answer1" etc.
5. The factual meaning of each question must come from the video content, not outside knowledge.
6. `correct_answer` should be a concatenated string of all answers separated by | separator, e.g., "n % i == 0|factors".
7. `starter_code` should be the code skeleton with blank points, identical to what appears in the question.
8. `test_cases` must contain 4 to 8 assert-style tests that verify all blank points are correct. Use complete code that fills all blanks.
9. `question_type` must be `fill-in-the-blank`.
10. `source_time` should be `unknown` if not available.
11. `source_excerpt` must quote the most relevant video text.
12. At least 3 questions should obviously follow one of the retrieved templates.
13. Do not add any extra text outside the JSON array.
14. Use plain JSON only, without markdown fences.

Return format:
[
  {{
    "question": "完整的題目描述（包含程式碼框架和填空點）",
    "correct_answer": "answer1|answer2|answer3",
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
