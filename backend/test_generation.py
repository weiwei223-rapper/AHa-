import sys
import os
from pathlib import Path

# Add the current directory to sys.path so we can import local modules
backend_path = r'C:\Users\user\Desktop\AHa\backend'
if backend_path not in sys.path:
    sys.path.append(backend_path)

try:
    import learning_pipeline
    import schema
    print("Successfully imported learning_pipeline")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

video_id = 1
title = "Python 基礎教學 - 布林值與邏輯運算"
video_link = "https://www.youtube.com/watch?v=onrMi-D7lvY"

print(f"Starting quiz generation for: {title}")
try:
    quiz = learning_pipeline.generate_quiz(video_id, title, video_link)
    print("\n--- QUIZ GENERATED ---")
    print(f"Quiz Type: {quiz.quiz_type}")
    print(f"Number of questions: {len(quiz.questions)}")
    
    for i, q in enumerate(quiz.questions):
        print(f"\nQ{i+1}: {q.question[:100]}...")
        print(f"Concept: {q.reference_concept}")
        print(f"Answer: {q.correct_answer}")
        print(f"Starter Code:\n{q.starter_code}")
        print("-" * 30)
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
