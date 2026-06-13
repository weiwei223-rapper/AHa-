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

router = APIRouter(prefix="/api", tags=["quizzes"])

@router.get("/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz_api(video_id: int, count: int = Query(5, ge=1, le=10), difficulty: str = Query("medium"), current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    if video.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")

    if not video.outline:
        raise HTTPException(status_code=400, detail="請先執行教材分析（Analyze）再生成測驗")

    pts_needed = count * 50
    if current_user.points < pts_needed: raise HTTPException(status_code=400, detail="點數不足")

    try:
        res = learning_pipeline.generate_quiz(video.id, video.title or "Video", video.video_link, count=count, existing_outline=video.outline, difficulty=difficulty)
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
                reference_concept=item.reference_concept  # 確保保存知識點標籤
            )
            db.add(q); db.flush()
            db.add(models.GenerationRecord(user_id=current_user.id, quiz_question_id=q.id, consumed_points=50)) 
        db.commit(); return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/quiz", response_model=schema.QuizResponse)
def generate_doc_quiz(doc_id: int, count: int = Query(5, ge=1, le=10), difficulty: str = Query("medium"), current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")

    if not doc.outline:
        raise HTTPException(status_code=400, detail="請先執行教材分析（Analyze）再生成測驗")
    
    pts_needed = count * 50
    if current_user.points < pts_needed: raise HTTPException(status_code=400, detail="點數不足")

    try:
        res = learning_pipeline.generate_quiz_from_document(doc.id, doc.title, doc.content_text, count=count, existing_outline=doc.outline, difficulty=difficulty)
        current_user.points -= len(res.questions) * 50
        for item in res.questions:
            db.add(models.QuizQuestion(
                user_id=current_user.id, 
                document_id=doc.id, 
                question_content=item.question, 
                reference_answer=item.correct_answer, 
                starter_code=item.starter_code, 
                test_cases_json=json.dumps(item.test_cases), 
                explanation=item.explanation,
                reference_concept=item.reference_concept  # 確保保存知識點標籤
            ))
        db.commit(); return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/quizzes/{video_id}/grade", response_model=schema.GradeResponse)
def grade_quiz(video_id: int, payload: schema.GradeRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    answer_count = len(payload.answers)
    q_list = db.query(models.QuizQuestion).filter(models.QuizQuestion.user_id == current_user.id)
    if video_id > 0: q_list = q_list.filter(models.QuizQuestion.video_id == video_id)
    elif payload.document_id: q_list = q_list.filter(models.QuizQuestion.document_id == payload.document_id)    
    questions = q_list.order_by(models.QuizQuestion.id.desc()).limit(answer_count).all()
    questions.reverse()
    details = []; correct = 0
    for idx, q in enumerate(questions):
        user_code = payload.answers[idx] if idx < len(payload.answers) else ""
        
        # Check for empty submission
        if not user_code.strip():
            details.append({
                "question_id": q.id, "question_text": q.question_content, "user_answer": user_code,
                "passed": False, "test_results": [], "reference_concept": q.reference_concept
            })
            continue

        test_cases = json.loads(q.test_cases_json or "[]")
        passed = True
        q_res = []
        
        for tc_raw in test_cases:
            # 判斷是新格式 {"input": [], "expected": ""} 還是舊格式 string
            try:
                tc = json.loads(tc_raw) if isinstance(tc_raw, str) and tc_raw.startswith("{") else tc_raw
            except:
                tc = tc_raw

            if isinstance(tc, dict) and "expected" in tc:
                # 新格式：函式測試
                input_args = tc.get("input", [])
                expected = str(tc.get("expected")).strip()
                
                # 建構測試腳本：將 solve(...) 的結果印出來
                args_str = ", ".join([json.dumps(a) for a in input_args]) if isinstance(input_args, list) else json.dumps(input_args)
                test_script = f"{user_code}\n\ntry:\n    print(str(solve({args_str})).strip())\nexcept Exception as e:\n    print(f'EXEC_ERROR:{{e}}')"
                
                actual_out, exec_err = code_compiler.execute_python_code(test_script)
                actual_clean = actual_out.strip()
                
                match = (actual_clean == expected) and not exec_err and "EXEC_ERROR:" not in actual_clean
                if not match: passed = False
                
                q_res.append({
                    "test_case": f"solve({args_str})", 
                    "passed": match, 
                    "expected": expected, 
                    "actual": actual_clean if "EXEC_ERROR:" not in actual_clean else "Error",
                    "error": exec_err or (actual_clean if "EXEC_ERROR:" in actual_clean else None)
                })
            else:
                # 舊格式：標準輸出比對 (Legacy Support)
                expected = str(tc).strip()
                # 執行參考解答
                ref_code = q.starter_code.replace('___', q.reference_answer)
                ref_out, _ = code_compiler.execute_python_code(ref_code)
                # 執行使用者解答
                user_out, user_err = code_compiler.execute_python_code(user_code)
                
                user_out_clean = user_out.strip()
                match = (user_out_clean == expected) or (user_out_clean == ref_out.strip())
                if user_err or not user_out_clean: match = False
                
                if not match: passed = False
                q_res.append({
                    "test_case": "Output Match", "passed": match, 
                    "expected": expected or ref_out.strip(), "actual": user_out_clean,
                    "error": user_err
                })
        
        if passed: correct += 1
        details.append({
            "question_id": q.id,
            "question_text": q.question_content,
            "user_answer": user_code,
            "reference_answer": q.reference_answer,
            "passed": passed,
            "test_results": q_res,
            "reference_concept": q.reference_concept
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
