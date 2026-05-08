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

@dataclass
class TranscriptResult:
    transcript: str
    source: str

def _call_llm(prompt: str) -> str:
    return ai_analyzer.generate_text_with_gemini([{"role": "user", "parts": [{"text": prompt}]}])

def _extract_json_array(payload: str) -> list[dict[str, Any]]:
    # 移除所有 Markdown
    payload = re.sub(r"```[a-z]*|```", "", payload).strip()
    
    # 尋找 [ ... ] 或 { ... }
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
        source_excerpt=None, # 已移除出題依據
        starter_code=str(item.get("starter_code") or ""),
        test_cases=item.get("test_cases") or ["assert True"],
    )

def analyze_video(video_id: int, title: str, video_link: str) -> schema.VideoAnalysisResponse:
    # 獲取逐字稿
    transcript = ai_analyzer.fetch_video_transcript(video_link) or "無逐字稿"
    outline = f"- 影片標題：{title}\n- 內容摘要：Python 程式教學"
    
    return schema.VideoAnalysisResponse(
        video_id=video_id, 
        video_title=title, 
        transcript_source="direct",
        transcript_excerpt=transcript[:500], 
        outline_markdown=outline,
        key_topics=[title], 
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
影片內容：{analysis.transcript_excerpt}

出題要求：
1. **不要**使用 'class Solution' 物件導向結構。
2. 使用直覺的「變數運算」或「簡單函式」風格。
3. 程式碼中必須包含清晰的中文注釋，標註填空處（例如：# --- 請在此處填寫 ---）。
4. 填空處請使用唯一的 `___`。
5. 題目敘述要包含：場景設定、輸入輸出說明。
6. 提供 **精確 3 個** 測試案例 (test_cases)，用於驗證邏輯正確性。
7. 使用繁體中文。

JSON 範例格式：
[
  {{
    "question": "場景描述 (例如：判斷成績是否及格...)",
    "reference_concept": "技術點 (例如：比較運算子)",
    "correct_answer": "答案內容",
    "explanation": "解析為何填寫此內容",
    "starter_code": "score = 80\\n# --- 請在下方補全「大於等於 60」的邏輯 ---\\nis_pass = ___\\nprint(is_pass)",
    "test_cases": ["print(80 >= 60)", "print(50 >= 60)", "print(60 >= 60)"]
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
