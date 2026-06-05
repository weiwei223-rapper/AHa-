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
    YoutubeLoader = None

OUTLINE_CHUNK_SIZE = 8000
OUTLINE_CHUNK_OVERLAP = 800

@dataclass
class TranscriptResult:
    transcript: str
    source: str

def _call_llm(prompt: str) -> tuple[str, dict]:
    return ai_analyzer.generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])

def _add_tokens(total: dict, current: dict):
    total["promptTokenCount"] += current.get("promptTokenCount", 0)
    total["candidatesTokenCount"] += current.get("candidatesTokenCount", 0)
    total["totalTokenCount"] += current.get("totalTokenCount", 0)

def _to_token_usage_schema(usage_dict: dict) -> schema.TokenUsage:
    return schema.TokenUsage(
        prompt_tokens=usage_dict.get("promptTokenCount", 0),
        completion_tokens=usage_dict.get("candidatesTokenCount", 0),
        total_tokens=usage_dict.get("totalTokenCount", 0)
    )

def _extract_json_array(payload: str) -> list[dict[str, Any]]:
    payload = re.sub(r"```[a-z]*|```", "", payload).strip()
    arr_match = re.search(r"\[.*\]", payload, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except:
            pass
    obj_match = re.search(r"\{.*\}", payload, re.DOTALL)
    if obj_match:
        try:
            return [json.loads(obj_match.group(0))]
        except:
            pass
    raise ValueError(f"Could not extract JSON from AI response")

def _normalize_question(item: dict[str, Any]) -> schema.QuizQuestion:
    return schema.QuizQuestion(
        question=str(item.get("question") or "請補全程式碼"),
        correct_answer=str(item.get("correct_answer") or ""),
        explanation=str(item.get("explanation") or ""),
        reference_concept=str(item.get("reference_concept") or "Python"),
        question_type="fill-in-the-blank",
        source_time="unknown",
        source_excerpt=None,
        starter_code=str(item.get("starter_code") or ""),

        # 將原本吃不到的 test_cases，改為接住 Prompt 產出的 expected_output
        test_cases=[str(item.get("expected_output") or "print('No output')")],
    )

def _parse_bullets(markdown: str) -> list[str]:
    topics: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            topic = stripped[2:].strip()
            if topic:
                topics.append(topic)
    return topics[:8]

def generate_outline(transcript: str, title: str) -> tuple[str, dict]:
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}
    if not transcript.strip():
        return "- 無法取得內容文字\n- 目前不能生成可靠的摘要", total_usage

    chunks = [transcript[i:i+OUTLINE_CHUNK_SIZE] for i in range(0, len(transcript), OUTLINE_CHUNK_SIZE - OUTLINE_CHUNK_OVERLAP)]
    chunk_summaries: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        prompt = f"""
請用繁體中文整理以下內容片段。
要求：
1. 用 3 到 5 點條列。
2. 每點聚焦在這段內容的具體重點。
3. 不要補外部知識。

標題：{title}
片段：{index}/{len(chunks)}
內容：
{chunk}
"""
        text, usage = _call_llm(prompt)
        chunk_summaries.append(text)
        _add_tokens(total_usage, usage)

    merged_prompt = f"""
請把以下分段摘要整合成一份重點整理，使用繁體中文 Markdown 條列。
要求：
1. 產出 4 到 8 點。
2. 每點精簡明確。

標題：{title}
分段摘要：
{chr(10).join(chunk_summaries)}
"""
    final_text, final_usage = _call_llm(merged_prompt)
    _add_tokens(total_usage, final_usage)
    return final_text, total_usage

def analyze_video(video_id: int, title: str, video_link: str) -> schema.VideoAnalysisResponse:
    transcript = ai_analyzer.fetch_video_transcript(video_link)
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}

    if not transcript:
        original_title = ai_analyzer.get_video_title(video_link) or title
        fallback_prompt = f"""
你是一位專業的 Python 導師。目前系統無法從影片中提取聲音，但我們知道這部影片的標題是「{original_title}」。      
請根據這個標題所涉及的 Python 技術主題，產出一份結構化的學習大綱。
要求：
1. 用 5 點條列說明該主題的核心語法、運算邏輯與常見應用。
2. 使用繁體中文。
"""
        outline, usage = _call_llm(fallback_prompt)
        _add_tokens(total_usage, usage)
        topics = _parse_bullets(outline)
        return schema.VideoAnalysisResponse(
            video_id=video_id, video_title=original_title, transcript_source="failed",
            transcript_excerpt="已啟動專家推理模式。",
            outline_markdown=outline,
            key_topics=topics, retrieved_chunks=[], vector_backend="none",
            generated_at=datetime.utcnow(),
            token_usage=_to_token_usage_schema(total_usage)
        )

    outline, usage = generate_outline(transcript, title)
    _add_tokens(total_usage, usage)
    topics = _parse_bullets(outline)

    return schema.VideoAnalysisResponse(
        video_id=video_id, video_title=title, transcript_source="direct",
        transcript_excerpt=transcript[:1000],
        full_transcript=transcript,
        outline_markdown=outline,
        key_topics=topics, retrieved_chunks=[], vector_backend="simple",
        generated_at=datetime.utcnow(),
        token_usage=_to_token_usage_schema(total_usage)
    )

def generate_quiz(video_id: int, title: str, video_link: str, count: int = 5, existing_outline: str | None = None) -> schema.QuizResponse:
    if existing_outline:
        transcript = ai_analyzer.fetch_video_transcript(video_link)
        return _generate_quiz_core(video_id, title, existing_outline, transcript[:1000] if transcript else "無法取得內容文字", count, is_video=True)
    analysis = analyze_video(video_id, title, video_link)
    return _generate_quiz_core(video_id, title, analysis.outline_markdown, analysis.transcript_excerpt, count, is_video=True)

def generate_quiz_from_document(doc_id: int, title: str, content: str, count: int = 5, existing_outline: str | None = None) -> schema.QuizResponse:
    if existing_outline:
        return _generate_quiz_core(doc_id, title, existing_outline, content[:1000], count, is_video=False)      
    outline, usage = generate_outline(content, title)
    return _generate_quiz_core(doc_id, title, outline, content[:1000], count, is_video=False)

def _generate_quiz_core(source_id: int, title: str, outline: str, snippet: str, count: int, is_video: bool) -> schema.QuizResponse:
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}

    prompt = f"""
[SYSTEM: RETURN RAW JSON ARRAY ONLY. NO TEXT AROUND IT.]
你是一位專業的 Python 程式語言導師。請根據提供的影片/文件內容，產出 {count} 題適合用來訓練學生「演算法思維」與「程式邏輯」的程式填空題。

標題：{title}
重點摘要：{outline}
部分內容：{snippet}

出題要求（邏輯訓練導向）：
1. **測驗核心**：題目必須包含具體的運算邏輯，例如：數學級數計算（如階乘、加總）、迴圈邊界條件（for/while）、條件分支（if/elif/else）、字串或陣列的資料處理（如解析特定字元、尋找極值）。
2. **填空設計**：填空處 `___` 不能只是單一語法關鍵字（如 with、open）。它必須是**「核心的邏輯運算式」**、**「完 整的條件判斷行」**或**「關鍵的變數更新」**。
   - 好的例子：`if ___:`（考驗條件設計）、`sum = ___`（考驗公式實作）、`while ___:`（考驗迴圈終止條件）。       
3. **鷹架引導註解（Scaffolding）**：
   - **必須**在關鍵邏輯步驟的上方，加上簡潔的「中文指引註解」（例如：`# 判斷是否為偶數以決定加減`、`# 計算目前數字的階乘並累加`），以鷹架方式引導學生完成邏輯實作。
4. **變數與輸入**：為了讓產出的程式碼可獨立執行與驗證，請用「直接宣告變數賦值」來取代 `input()`。
5. **架構限制**：嚴禁使用 'class Solution' 或複雜的物件導向架構。請保持為直觀的結構化程式設計，需要時可定義單一 函式（如 `def factorial(N):`）。
6. **手寫輸出追蹤**：每題必須設計「預期輸出」，用以模擬「看 code 寫出輸出結果」的程式碼追蹤能力。

JSON 格式要求：
[
  {{
    "question": "題目情境說明（例如：請完成以下程式碼以計算 N 的階乘）",
    "reference_concept": "迴圈控制 / 數學邏輯 / 條件判斷 / 字串處理",
    "correct_answer": "填空處的正確程式碼（即填入 ___ 的內容）",
    "expected_output": "填空完成後，完整執行該段程式碼會印出的標準輸出結果",
    "explanation": "針對此邏輯實作的原理、變數變化過程與易錯點解析",
    "starter_code": "含有 ___ 的完整程式碼（必須包含適當的引導註解與最後的 print 驗證行）"
  }}
]"""


    try:
        payload, usage = _call_llm(prompt)
        _add_tokens(total_usage, usage)
        raw_questions = _extract_json_array(payload)
        questions = [_normalize_question(item) for item in raw_questions[:count]]

        return schema.QuizResponse(
            video_id=source_id if is_video else None,
            document_id=source_id if not is_video else None,
            video_title=title,
            quiz_type="mixed_styles",
            questions=questions,
            token_usage=_to_token_usage_schema(total_usage)
        )
    except Exception as e:
        print(f"Error in quiz generation: {e}")
        fallback = ai_analyzer.generate_fallback_questions(title, outline=outline, count=count)
        return schema.QuizResponse(
            video_id=source_id if is_video else None,
            document_id=source_id if not is_video else None,
            video_title=title,
            quiz_type="fallback",
            questions=fallback,
            token_usage=_to_token_usage_schema(total_usage)
        )
