# AI-Powered Quiz Generation - Setup Guide

## 📋 Overview
This guide explains how to set up and use the AI-powered quiz generation feature that analyzes video content and generates relevant quiz questions using Google Gemini API.

## ✨ New Features

### 1. **AI-Powered Quiz Generation**
   - Videos are analyzed using Google Gemini AI
   - Quiz questions are generated based on actual video content
   - Questions are in Traditional Chinese
   - 5 multiple-choice questions per video

### 2. **Streamlined User Experience**
   - "📝 生成測驗" button on each video in Learning Material page
   - One-click quiz generation
   - Auto-loading quiz when navigating from Video page

## 🚀 Setup Instructions

### Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**New dependencies added:**
- `google-generativeai` - For Gemini API integration
- `python-dotenv` - For environment variable management
- `requests` - For HTTP requests

### Step 2: Configure API Key

**Important:** Your Google Generative AI API key must be configured.

1. Open `backend/API_key.env`
2. Ensure the following line exists:
   ```
   AI_API_KEY=your_google_generative_ai_key_here
   ```
3. Replace `your_google_generative_ai_key_here` with your actual API key

**Getting an API Key:**
- Visit: https://makersuite.google.com/app/apikey
- Create a new project
- Generate an API key
- Copy it to `API_key.env`

### Step 3: Start Backend Server

```bash
cd backend
python -m uvicorn main:app --reload
```

The API will run at: `http://localhost:8000`

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 5: Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will run at: `http://localhost:5173`

## 📝 How to Use

### Upload a Video
1. Navigate to **"Learning Material"** page
2. Enter video title (optional)
3. Enter video link (YouTube or other video URLs)
4. Click **"上傳影片連結"** (Upload Video Link)

### Generate Quiz
1. Find the uploaded video in the list
2. Click **"📝 生成測驗"** (Generate Quiz) button
3. Wait while AI analyzes the video content
4. Quiz questions will be generated automatically

### Take Quiz
1. Read each question carefully
2. Select your answer from 4 options
3. Use navigation buttons to move between questions
4. Click **"完成測驗"** (Complete Quiz) on the last question
5. Review results and correct answers

## 🔄 How It Works

### Technical Flow

```
User clicks "生成測驗" button
         ↓
Navigate to Quiz page with ?videoId=X parameter
         ↓
Frontend fetches quiz from backend
         ↓
Backend receives /api/videos/{videoId}/quiz request
         ↓
Backend initializes Gemini AI with API key
         ↓
AI analyzes video title and URL
         ↓
AI generates 5 relevant quiz questions
         ↓
Questions are returned as JSON with format:
{
  "video_id": number,
  "video_title": string,
  "questions": [
    {
      "question": "Question text",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "correct_answer": 0
    }
  ]
}
         ↓
Frontend displays quiz for user to complete
         ↓
Results are saved locally and to backend database
```

## 📁 File Changes

### New Files
- `backend/ai_analyzer.py` - AI integration module

### Modified Files
- `backend/requirements.txt` - Added AI dependencies
- `backend/main.py` - Updated quiz endpoint to use AI
- `frontend/src/pages/Video.tsx` - Added "Generate Quiz" button
- `frontend/src/pages/Quiz.tsx` - Added auto-loading from URL parameter

## ⚙️ Environment Variables

### `backend/API_key.env`
```
AI_API_KEY=your_api_key_here
```

## 🛠️ Troubleshooting

### "AI_API_KEY not found" Error
- **Solution:** Check that `API_key.env` exists and has the correct key
- Restart the backend server after updating the key

### "Failed to generate quiz" Error
- **Solution:** Verify your Google Generative AI API key is valid
- Check that you have sufficient API quota
- The system will fall back to generic questions if AI fails

### Connection Errors
- **Frontend → Backend:** Ensure backend is running on `http://localhost:8000`
- **API Key:** Verify the API key is correct and has proper permissions
- **CORS:** Backend has CORS enabled for `http://localhost:5173`

### Slow Quiz Generation
- **Normal behavior:** AI analysis may take 5-10 seconds
- Large context or complex prompts may take longer
- This is expected for the first request while AI processes

## 📊 Quiz Features

### Question Format
- **Type:** Multiple choice (4 options per question)
- **Language:** Traditional Chinese (繁體中文)
- **Total:** 5 questions per quiz
- **Content:** Based on video title/URL analysis

### Scoring
- Score calculated as: correct_answers / total_questions
- Percentage displayed with emoji feedback:
  - 🎉 80% or higher: Excellent!
  - 👍 60-79%: Good!
  - 💪 Below 60%: Keep trying!

### Result Storage
- Results saved to local browser storage (localStorage)
- Also saved to backend database for user history
- Can review past results in Profile page

## 🔒 Privacy & Security

- Video URLs are only used for title extraction and AI analysis
- Video content is NOT downloaded or stored
- API keys are stored in environment variables only
- Quiz responses are stored locally and in secure database

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify all dependencies are installed
3. Ensure backend and frontend are running
4. Check browser console for error messages

## 🎯 Future Enhancements

Possible improvements for future versions:
- Support for video file uploads (not just links)
- Adjustable quiz difficulty levels
- Different question types (True/False, Fill-in-the-blank)
- Multi-language support
- Quiz scheduling and reminders
- AI-powered answer explanations

---

**Version:** 1.0
**Last Updated:** April 21, 2026
