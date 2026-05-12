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
        test_cases=item.get("test_cases") or ["assert True"],
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
        return "- 無法取得影片逐字稿\n- 目前不能生成可靠的影片摘要", total_usage

    # 簡單分段處理
    chunks = [transcript[i:i+OUTLINE_CHUNK_SIZE] for i in range(0, len(transcript), OUTLINE_CHUNK_SIZE - OUTLINE_CHUNK_OVERLAP)]
    chunk_summaries: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        prompt = f"""
請用繁體中文整理以下影片逐字稿片段。
要求：
1. 用 3 到 5 點條列。
2. 每點聚焦在這段內容的具體重點。
3. 不要補外部知識。

影片標題：{title}
片段：{index}/{len(chunks)}
逐字稿：
{chunk}
"""
        text, usage = _call_llm(prompt)
        chunk_summaries.append(text)
        _add_tokens(total_usage, usage)

    merged_prompt = f"""
請把以下分段摘要整合成一份影片重點整理，使用繁體中文 Markdown 條列。
要求：
1. 產出 4 到 8 點。
2. 每點精簡明確。

影片標題：{title}
分段摘要：
{chr(10).join(chunk_summaries)}
"""
    final_text, final_usage = _call_llm(merged_prompt)
    _add_tokens(total_usage, final_usage)
    return final_text, total_usage

def analyze_video(video_id: int, title: str, video_link: str) -> schema.VideoAnalysisResponse:
    # 獲取逐字稿
    transcript = ai_analyzer.fetch_video_transcript(video_link)
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}
    
    if not transcript:
        # 抓取 YouTube 原始標題以利精準推理 (避免受使用者自定義標題干擾)
        original_title = ai_analyzer.get_video_title(video_link) or title
        
        # 零失敗備援：讓 AI 以專家身份根據「原始標題」進行知識推理
        fallback_prompt = f"""
你是一位專業的 Python 導師。目前系統無法從影片中提取聲音，但我們知道這部影片的原始標題是「{original_title}」。
請根據這個標題所涉及的 Python 技術主題，產出一份結構化的學習大綱。
要求：
1. 用 5 點條列說明該主題的核心語法、運算邏輯與常見應用。
2. 內容要具體且具備技術深度。
3. 使用繁體中文。
"""
        outline, usage = _call_llm(fallback_prompt)
        _add_tokens(total_usage, usage)
        topics = _parse_bullets(outline)
        return schema.VideoAnalysisResponse(
            video_id=video_id, video_title=original_title, transcript_source="failed",
            transcript_excerpt="系統目前因 YouTube 限制無法取得音軌，已啟動『專家推理模式』根據影片原始標題生成學習重點。", 
            outline_markdown=outline,
            key_topics=topics, retrieved_chunks=[], vector_backend="none",
            generated_at=datetime.utcnow(),
            token_usage=_to_token_usage_schema(total_usage)
        )
    
    outline, usage = generate_outline(transcript, title)
    _add_tokens(total_usage, usage)
    topics = _parse_bullets(outline)
    
    return schema.VideoAnalysisResponse(
        video_id=video_id, 
        video_title=title, 
        transcript_source="direct",
        transcript_excerpt=transcript[:1000], 
        outline_markdown=outline,
        key_topics=topics, 
        retrieved_chunks=[], 
        vector_backend="simple",
        generated_at=datetime.utcnow(),
        token_usage=_to_token_usage_schema(total_usage)
    )

def generate_quiz(video_id: int, title: str, video_link: str, count: int = 5) -> schema.QuizResponse:
    analysis = analyze_video(video_id, title, video_link)
    total_usage = {"promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0}
    
    if analysis.token_usage:
        total_usage["promptTokenCount"] += analysis.token_usage.prompt_tokens
        total_usage["candidatesTokenCount"] += analysis.token_usage.completion_tokens
        total_usage["totalTokenCount"] += analysis.token_usage.total_tokens

    # 零失敗備援偵測：若分析結果顯示 failed，直接進入標題推理
    if analysis.transcript_source == "failed":
        questions = ai_analyzer.generate_fallback_questions(title, outline=analysis.outline_markdown, count=count)
        return schema.QuizResponse(
            video_id=video_id, 
            video_title=title, 
            quiz_type="technical_inference", 
            questions=questions,
            token_usage=_to_token_usage_schema(total_usage)
        )

    prompt = f"""
[SYSTEM: RETURN RAW JSON ARRAY ONLY. NO TEXT AROUND IT.]
你是一位親切的 Python 導師。請根據影片內容產出 {count} 題「直覺式」的程式填空題。

影片標題：{title}
大綱：{analysis.outline_markdown}
影片部分內容：{analysis.transcript_excerpt}

出題要求：
1. **不要**使用 'class Solution' 物件導向結構。
2. 使用直覺的「變數運算」或「簡單函式」風格。
3. **嚴禁使用 input() 函式**。
4. 程式碼中必須包含清晰的中文注釋，標註填空處（例如：# --- 請在此處填寫 ---）。
5. 填空處請使用唯一的 `___`。
6. 題目敘述要包含：場景設定、輸入輸出說明。
7. 提供 **精確 3 個** 測試案例 (test_cases)，每個案例應為一行程式碼，並使用 `print()` 輸出結果。
8. 使用繁體中文。

JSON 範例格式：
[
  {{
    "question": "場景描述 (例如：判斷成績是否及格...)",
    "reference_concept": "技術點 (例如：比較運算子)",
    "correct_answer": "答案內容",
    "explanation": "解析為何填寫此內容",
    "starter_code": "def check(score):\\n    # --- 請在下方補全邏輯 ---\\n    is_pass = ___\\n    return is_pass",
    "test_cases": ["print(check(80))", "print(check(50))", "print(check(60))"]
  }}
]
"""
    try:
        payload, usage = _call_llm(prompt)
        _add_tokens(total_usage, usage)
        raw_questions = _extract_json_array(payload)
        questions = [_normalize_question(item) for item in raw_questions[:count]]
        return schema.QuizResponse(
            video_id=video_id, 
            video_title=title, 
            quiz_type="coding", 
            questions=questions,
            token_usage=_to_token_usage_schema(total_usage)
        )
    except Exception as e:
        print(f"Error in generate_quiz: {e}")
        # 極速備援題目
        fallback_questions = ai_analyzer.generate_fallback_questions(title, outline=analysis.outline_markdown, count=count)
        return schema.QuizResponse(
            video_id=video_id, 
            video_title=title, 
            quiz_type="fallback", 
            questions=fallback_questions,
            token_usage=_to_token_usage_schema(total_usage)
        )
