import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import or_
from sqlalchemy.orm import Session
import models
import database
import schema
import learning_pipeline
import code_compiler
import ai_analyzer
import email_service
from report_utils import process_error_report_task
from auth_utils import get_current_user

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])

@router.get("/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz_api(video_id: int, count: int = Query(5, ge=1, le=10), current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    if video.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    if not video.outline:
        raise HTTPException(status_code=400, detail="請先進行教材分析 (Analyze) 後再生成測驗")

    pts_needed = count * 50
    if current_user.points < pts_needed: raise HTTPException(status_code=400, detail="點數不足")

    try:
        res = learning_pipeline.generate_quiz(video.id, video.title or "Video", video.video_link, count=count, existing_outline=video.outline)
        current_user.points -= len(res.questions) * 50
        for item in res.questions:
            q = models.QuizQuestion(
                user_id=current_user.id, 
                video_id=video.id, 
                question_content=item.question, 
                reference_answer=item.correct_answer, 
                starter_code=item.starter_code, 
                test_cases_json=json.dumps(item.test_cases), 
                explanation=item.explanation,
                reference_concept=item.reference_concept # Added
            )
            db.add(q); db.flush()
            db.add(models.GenerationRecord(user_id=current_user.id, quiz_question_id=q.id, consumed_points=50))
        db.commit(); return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/quiz", response_model=schema.QuizResponse)
def generate_doc_quiz(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    if not doc.outline:
        raise HTTPException(status_code=400, detail="請先進行文件分析 (Analyze) 後再生成測驗")
    
    res = learning_pipeline.generate_quiz_from_document(doc.id, doc.title, doc.content_text, count=5, existing_outline=doc.outline)
    pts_needed = len(res.questions) * 50
    if current_user.points < pts_needed: raise HTTPException(status_code=400, detail="點數不足")
    
    current_user.points -= pts_needed
    for item in res.questions:
        db.add(models.QuizQuestion(
            user_id=current_user.id, 
            document_id=doc.id, 
            question_content=item.question, 
            reference_answer=item.correct_answer, 
            starter_code=item.starter_code, 
            test_cases_json=json.dumps(item.test_cases), 
            explanation=item.explanation,
            reference_concept=item.reference_concept # Added
        ))
    db.commit(); return res

@router.post("/{video_id}/grade", response_model=schema.GradeResponse)
def grade_quiz(video_id: int, payload: schema.GradeRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    answer_count = len(payload.answers)
    q_list = db.query(models.QuizQuestion).filter(models.QuizQuestion.user_id == current_user.id)
    if video_id > 0: q_list = q_list.filter(models.QuizQuestion.video_id == video_id)
    elif payload.document_id: q_list = q_list.filter(models.QuizQuestion.document_id == payload.document_id)
    questions = q_list.order_by(models.QuizQuestion.id.desc()).limit(answer_count).all()
    questions.reverse()
    details = []; correct = 0
    for idx, q in enumerate(questions):
        user_code = payload.answers[idx]; test_cases = json.loads(q.test_cases_json or "[]")
        passed = False; q_res = []
        
        # 如果沒有測試案例，則進行一次預設的完整執行比對
        run_targets = test_cases if test_cases else ["# Default check"]
        
        all_passed = True
        for tc in run_targets:
            # 確保 tc 是有效的代碼，如果只是純文字則包裝成註解以免造成語法錯誤
            tc_code = tc if tc.strip().startswith("#") or "(" in tc or "=" in tc else f"# {tc}"
            
            ref_script = f"{q.starter_code.replace('___', q.reference_answer)}\n{tc_code}"
            user_script = f"{user_code}\n{tc_code}"
            
            ref_out, ref_err = code_compiler.execute_python_code(ref_script)
            user_out, user_err = code_compiler.execute_python_code(user_script)
            
            # 如果使用者代碼有語法錯誤或執行錯誤，且參考代碼沒有，則判定失敗
            if user_err and not ref_err:
                match = False
            else:
                match = ref_out.strip() == user_out.strip()
            
            # 如果兩邊都沒有輸出且沒有錯誤，或是輸出的比對失敗，進行字串保險比對
            # 這能處理填充 ___ 卻沒有 print 的情況
            is_placeholder = "___" in user_code
            if is_placeholder:
                match = False
            elif not match and not test_cases:
                # 最後手段：直接比對填充後的字串是否一致
                ref_full = q.starter_code.replace('___', q.reference_answer).strip()
                if user_code.strip() == ref_full:
                    match = True

            if not match: all_passed = False
            q_res.append({
                "test_case": tc, 
                "passed": match, 
                "expected": ref_out.strip() if not ref_err else f"Error: {ref_err}", 
                "actual": user_out.strip() if not user_err else f"Error: {user_err}"
            })
        
        if all_passed and len(run_targets) > 0:
            passed = True
            correct += 1
            
        details.append({
            "question_id": q.id,
            "question_text": q.question_content,
            "reference_concept": q.reference_concept, # Added
            "user_answer": user_code,
            "reference_answer": q.reference_answer,
            "passed": passed,
            "test_results": q_res
        })
    return schema.GradeResponse(total_score=round(correct/len(questions)*100) if questions else 0, details=details)

@router.get("/quiz-results", response_model=List[schema.QuizResultResponse])
def get_quiz_results(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    return db.query(models.QuizResult).filter(models.QuizResult.user_id == current_user.id).order_by(models.QuizResult.completed_at.desc()).all()

@router.post("/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    res = models.QuizResult(user_id=current_user.id, video_id=payload.video_id, document_id=payload.document_id, score=payload.score, total_questions=payload.total_questions, title=payload.title, details_json=payload.details_json)
    db.add(res); db.commit(); db.refresh(res); return res

@router.get("/quiz-drafts", response_model=List[schema.QuizDraftResponse])
def get_all_drafts(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    drafts = db.query(models.QuizDraft).filter(models.QuizDraft.user_id == current_user.id).all()
    for d in drafts: d.video_title = d.video.title if d.video else (d.document.title if d.document else "Unknown")
    return drafts

@router.post("/quiz-drafts", response_model=schema.QuizDraftResponse)
def upsert_quiz_draft(payload: schema.QuizDraftBase, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    q = db.query(models.QuizDraft).filter(models.QuizDraft.user_id == current_user.id)
    if payload.video_id: q = q.filter(models.QuizDraft.video_id == payload.video_id)
    elif payload.document_id: q = q.filter(models.QuizDraft.document_id == payload.document_id)
    draft = q.first()
    if draft: draft.draft_json = payload.draft_json; draft.updated_at = datetime.now()
    else:
        draft = models.QuizDraft(user_id=current_user.id, video_id=payload.video_id, document_id=payload.document_id, draft_json=payload.draft_json)
        db.add(draft)
    db.commit(); db.refresh(draft); return draft

@router.delete("/quiz-drafts/{video_id}")
def delete_quiz_draft(video_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    db.query(models.QuizDraft).filter(models.QuizDraft.user_id == current_user.id, or_(models.QuizDraft.video_id == video_id, models.QuizDraft.document_id == video_id)).delete()
    db.commit(); return {"message": "Deleted"}

@router.post("/quiz-results/{result_id}/report-error", response_model=schema.QuizResultResponse)
def report_quiz_error(result_id: int, payload: schema.ErrorReportRequest, background_tasks: BackgroundTasks, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    res = db.query(models.QuizResult).filter(models.QuizResult.id == result_id).first()
    if not res: raise HTTPException(status_code=404, detail="Quiz result not found")
    if res.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    res.error_report = payload.error_report
    db.commit(); db.refresh(res)
    
    background_tasks.add_task(process_error_report_task, res.id, "quiz", current_user.id)
    return res
