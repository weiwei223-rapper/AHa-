from sqlalchemy.orm import Session
import models
import database
import ai_analyzer
import email_service

def process_error_report_task(report_id: int, report_type: str, user_id: int):
    db = database.SessionLocal()
    try:
        if report_type == "quiz":
            res = db.query(models.QuizResult).filter(models.QuizResult.id == report_id).first()
            source_content = res.details_json or ""
            item_title = res.title or "測驗題目"
        elif report_type == "video":
            res = db.query(models.Video).filter(models.Video.id == report_id).first()
            source_content = res.outline or ""
            item_title = res.title or "影片大綱"
        elif report_type == "document":
            res = db.query(models.Document).filter(models.Document.id == report_id).first()
            source_content = res.outline or ""
            item_title = res.title or "文件大綱"
        elif report_type == "feedback":
            res = db.query(models.AIFeedback).filter(models.AIFeedback.id == report_id).first()
            source_content = res.ai_message or ""
            item_title = "AI 聊天回覆"
        else: return

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not res or not user: return

        is_valid, reason = ai_analyzer.validate_error_report(res.error_report, source_content, report_type)
        
        refund_points = 0
        if is_valid:
            # 點數歸還邏輯：返還 1.5 倍點數 (假設單題 50 點)
            refund_points = 75 
            user.points += refund_points
            db.commit()

        email_service.send_refund_email(
            user_email=user.email,
            user_name=user.name,
            item_title=item_title,
            is_valid=is_valid,
            refund_points=refund_points,
            reason=reason
        )
    except Exception as e:
        print(f"DEBUG: Error processing report task: {e}")
    finally:
        db.close()
