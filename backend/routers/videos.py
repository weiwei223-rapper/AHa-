import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import database
import schema
import ai_analyzer
import learning_pipeline
from auth_utils import get_current_user

router = APIRouter(prefix="/api/videos", tags=["videos"])

@router.get("", response_model=List[schema.VideoResponse])
def get_videos(user_id: Optional[int] = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    target_user_id = user_id if user_id is not None else current_user.id
    if target_user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    return db.query(models.Video).filter(models.Video.user_id == target_user_id).order_by(models.Video.id.desc()).all()

@router.get("/{video_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_video(video_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    if video.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        analysis = learning_pipeline.analyze_video(video.id, video.title or "Video", video.video_link)
        pts = math.ceil(((analysis.token_usage.total_tokens if analysis.token_usage else 0) / 2000) * 100 / 10) * 10
        if current_user.points < pts: raise HTTPException(status_code=400, detail="點數不足")
        current_user.points -= pts
        db.add(models.UploadRecord(user_id=current_user.id, video_id=video.id, consumed_points=pts))
        if analysis.outline_markdown: video.outline = analysis.outline_markdown
        db.commit(); db.refresh(video)
        return analysis
    except Exception as e: 
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    title = ai_analyzer.get_video_title(payload.video_link) or "Untitled"
    if not ai_analyzer.is_python_related(title, ai_analyzer.fetch_video_transcript(payload.video_link)[:1500]):
        raise HTTPException(status_code=400, detail="僅支援 Python 相關影片")
    video = models.Video(video_link=payload.video_link, title=payload.title or title, user_id=current_user.id)
    db.add(video); db.commit(); db.refresh(video)
    return video

@router.delete("/{video_id}")
def delete_video(video_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    if video.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
