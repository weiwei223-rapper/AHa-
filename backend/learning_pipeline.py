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
        test_cases=item.get("test_cases") or ["print('No tests')"],
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

def generate_quiz(video_id: int, title: str, video_link: str, count: int = 5) -> schema.QuizResponse:
    analysis = analyze_video(video_id, title, video_link)
    return _generate_quiz_core(video_id, title, analysis.outline_markdown, analysis.transcript_excerpt, count, is_video=True)

def generate_quiz_from_document(doc_id: int, title: str, content: str, count: int = 5) -> schema.QuizResponse:
    outline, usage = generate_outline(content, title)
    return _generate_quiz_core(doc_id, title, outline, content[:1000], count, is_video=False)

def _generate_quiz_core(source_id: int, title: str, outline: str, snippet: str, count: int, is_video: bool) -> schema.QuizResponse:
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}
    
    prompt = f"""
[SYSTEM: RETURN RAW JSON ARRAY ONLY. NO TEXT AROUND IT.]
你是一位專業的 Python 導師。請根據提供內容產出 {count} 題適合「紙筆測驗」的手寫填空題。

標題：{title}
重點摘要：{outline}
部分內容：{snippet}

出題要求（手寫題導向）：
1. **題型混合要求**：請平均分配以下四種風格：
   - 『關鍵字熟練』：針對 Python 保留字或內建函數（考查手寫拼字與語法精準度）。
   - 『邏輯運算』：針對 if/while/for 邏輯判斷與邊界條件。
   - 『資料處理』：針對串列、字典操作或字串切片（考查手寫索引值的計算）。
   - 『函式架構』：針對參數傳遞、預設值或回傳值架構。
2. **手寫題規格**：
   - 程式碼必須是一個完整、可閱讀的獨立情境（非片段），讓學生能一眼看懂這段程式的邏輯。
   - 填空處使用唯一的 `___`，該填空處應為「一個關鍵字」、「一個運算式」或「一個變數」，避免讓學生手寫過長的程式碼。
3. **嚴禁**使用 'class Solution' 或物件導向。
4. **嚴禁**使用 input()。
5. 程式碼必須包含中文註釋以引導解題。
6. **手寫輸出追蹤**：除了程式碼填空外，每題必須設計「當此程式執行時，預期在螢幕上印出的正確結果」，用以模擬手寫考卷中的「看 code 寫出輸出結果」題型。
7. 使用繁體中文。

JSON 格式要求：
[
  {{
    "question": "題目情境與手寫引導說明",
    "reference_concept": "關鍵字熟練 / 邏輯運算 / 資料處理 / 函式架構",
    "correct_answer": "填空處的正確程式碼（答案）",
    "expected_output": "填空完成後，該段程式碼完整執行會印出的標準輸出（手寫閱卷用）",
    "explanation": "針對該填空原理與手寫易錯點的詳細解析",
    "starter_code": "含有 ___ 的完整程式碼（包含最後用來檢驗輸出的 print 行）"
  }}
]


"""
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
