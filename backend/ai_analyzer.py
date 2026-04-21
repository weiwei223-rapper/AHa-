"""
AI-powered video content analyzer using Google Gemini API
Analyzes video content and generates quiz questions
"""

import os
import json
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
import schema

# Load environment variables
load_dotenv(dotenv_path="./API_key.env")

def init_gemini():
    """Initialize Gemini AI client"""
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("AI_API_KEY not found in environment variables")
    genai.configure(api_key=api_key)
    return genai

def extract_video_metadata(video_link: str, title: str) -> dict:
    """Extract metadata about the video from its link"""
    metadata = {
        "is_youtube": "youtube.com" in video_link or "youtu.be" in video_link,
        "is_playlist": "playlist" in video_link,
        "video_link": video_link,
        "title": title,
    }
    return metadata

def analyze_video_content_with_ai(video_link: str, title: str) -> List[schema.QuizQuestion]:
    """
    Analyze video content using Gemini AI and generate quiz questions
    
    Args:
        video_link: URL of the video
        title: Title of the video
        
    Returns:
        List of quiz questions
    """
    try:
        # Initialize Gemini
        init_gemini()
        model = genai.GenerativeModel('gemini-pro')
        
        # Extract metadata
        metadata = extract_video_metadata(video_link, title)
        
        # Create a detailed prompt for quiz generation
        prompt = f"""
Based on the following video information, generate 5 multiple-choice quiz questions in Traditional Chinese.

Video Title: {title}
Video Link: {video_link}

Requirements:
1. Create 5 quiz questions that test understanding of the video content
2. Each question should have 4 multiple-choice options
3. Include the index (0-3) of the correct answer
4. Questions should be educational and challenging
5. Return ONLY a valid JSON array with no additional text

For playlist/course videos: Focus on learning objectives and key concepts
For tutorial videos: Focus on practical skills and implementation details
For general videos: Focus on main topics and takeaways

JSON format:
[
  {{
    "question": "Question text in Traditional Chinese",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_answer": 0
  }},
  ...
]

Please generate the quiz questions now:
"""
        
        # Generate quiz questions
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("Empty response from Gemini AI")
        
        # Parse the JSON response
        quiz_data = parse_ai_response(response.text)
        
        # Convert to schema objects
        questions = []
        for item in quiz_data:
            question = schema.QuizQuestion(
                question=item.get("question", ""),
                options=item.get("options", []),
                correct_answer=item.get("correct_answer", 0)
            )
            questions.append(question)
        
        return questions
        
    except Exception as e:
        print(f"Error analyzing video with AI: {e}")
        # Fallback to basic questions if AI fails
        return generate_fallback_questions(title)

def parse_ai_response(response_text: str) -> List[dict]:
    """
    Parse the AI response and extract JSON
    
    Args:
        response_text: Raw response from Gemini API
        
    Returns:
        List of question dictionaries
    """
    try:
        # Try to extract JSON from the response
        # Sometimes the AI includes extra text before/after JSON
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON array found in response")
        
        json_str = response_text[start_idx:end_idx]
        quiz_data = json.loads(json_str)
        
        # Validate the data structure
        if not isinstance(quiz_data, list) or len(quiz_data) == 0:
            raise ValueError("Invalid quiz data structure")
        
        # Ensure each question has required fields
        for item in quiz_data:
            if not all(key in item for key in ["question", "options", "correct_answer"]):
                raise ValueError("Missing required fields in question")
            if len(item["options"]) != 4:
                raise ValueError("Each question must have exactly 4 options")
        
        return quiz_data
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        raise ValueError(f"Failed to parse AI response as JSON: {e}")
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        raise

def generate_fallback_questions(title: str) -> List[schema.QuizQuestion]:
    """
    Generate basic fallback questions if AI analysis fails
    
    Args:
        title: Video title
        
    Returns:
        List of basic quiz questions
    """
    return [
        schema.QuizQuestion(
            question=f"關於 '{title}' 的影片，你獲得什麼主要知識？",
            options=["新知識", "新技能", "新觀點", "理論概念"],
            correct_answer=0
        ),
        schema.QuizQuestion(
            question=f"這個 '{title}' 影片適合什麼學習者？",
            options=["初學者", "進階者", "專家", "所有人"],
            correct_answer=3
        ),
        schema.QuizQuestion(
            question=f"你會推薦 '{title}' 這個影片嗎？",
            options=["會", "可能會", "不確定", "不會"],
            correct_answer=0
        ),
        schema.QuizQuestion(
            question=f"'{title}' 影片內容的難度？",
            options=["簡單", "中等", "困難", "非常困難"],
            correct_answer=1
        ),
        schema.QuizQuestion(
            question=f"看完 '{title}' 後，你想學習什麼？",
            options=["相關進階課題", "實踐應用", "進一步深化", "保持現狀"],
            correct_answer=0
        )
    ]
