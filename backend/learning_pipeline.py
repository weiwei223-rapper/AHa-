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

def _call_llm(prompt: str) -> str:
    return ai_analyzer.generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])

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

def generate_outline(transcript: str, title: str) -> str:
    if not transcript.strip():
        return "- 無法取得影片逐字稿\n- 目前不能生成可靠的影片摘要"

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
        chunk_summaries.append(_call_llm(prompt))

    merged_prompt = f"""
請把以下分段摘要整合成一份影片重點整理，使用繁體中文 Markdown 條列。
要求：
1. 產出 4 到 8 點。
2. 每點精簡明確。

影片標題：{title}
分段摘要：
{chr(10).join(chunk_summaries)}
"""
    return _call_llm(merged_prompt)

def analyze_video(video_id: int, title: str, video_link: str) -> schema.VideoAnalysisResponse:
    # 獲取逐字稿
    transcript = ai_analyzer.fetch_video_transcript(video_link)
    if not transcript:
        # 零失敗備援：如果完全沒有字幕也無法轉譯，使用「標題」進行推理分析
        outline = generate_outline(f"這是一部名為「{title}」的教學影片。", title)
        topics = _parse_bullets(outline)
        return schema.VideoAnalysisResponse(
            video_id=video_id, video_title=title, transcript_source="failed",
            transcript_excerpt="系統無法取得影片聲音或字幕，已轉為使用「影片標題」進行推理分析。", 
            outline_markdown=outline,
            key_topics=topics, retrieved_chunks=[], vector_backend="none",
            generated_at=datetime.utcnow()
        )
    
    outline = generate_outline(transcript, title)
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
        generated_at=datetime.utcnow()
    )

def generate_quiz(video_id: int, title: str, video_link: str) -> schema.QuizResponse:
    analysis = analyze_video(video_id, title, video_link)
    
    prompt = f"""
[SYSTEM: RETURN RAW JSON ARRAY ONLY. NO TEXT AROUND IT.]
你是一位親切的 Python 導師。請根據影片內容產出 5 題「直覺式」的程式填空題。

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
        payload = _call_llm(prompt)
        raw_questions = _extract_json_array(payload)
        questions = [_normalize_question(item) for item in raw_questions]
        return schema.QuizResponse(video_id=video_id, video_title=title, quiz_type="coding", questions=questions)
    except Exception as e:
        print(f"Error in generate_quiz: {e}")
        # 極速備援題目
        return schema.QuizResponse(
            video_id=video_id, video_title=title, quiz_type="fallback",
            questions=[_normalize_question({
                "question": f"場景：判斷開關狀態。請補全邏輯，使其回傳 True。",
                "correct_answer": "True",
                "starter_code": "# --- 請在此填入 True ---\\nresult = ___",
                "test_cases": ["print(True)"]
            })]
        )
