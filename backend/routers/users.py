from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
import database
import schema
import auth_schemas
from auth_utils import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

# --- Sign-in / Daily Check-in Logic ---
SIGNIN_REWARDS = {1: 20, 2: 20, 3: 25, 4: 20, 5: 20, 6: 20, 7: 30}

def get_cycle_day(consecutive_days: int) -> int:
    if consecutive_days <= 0:
        return 0
    return ((consecutive_days - 1) % 7) + 1

def calculate_total_achievement_points(user: models.User, db: Session) -> int:
    video_count = db.query(models.Video).filter(models.Video.user_id == user.id, models.Video.outline != None).count()
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user.id).all()
    question_count = sum(r.total_questions for r in quiz_results) if quiz_results else 0
    total = 0
    for threshold in [1, 5, 10]:
        if video_count >= threshold: total += 200
    for threshold in [1, 5, 15, 30, 50, 100]:
        if question_count >= threshold: total += 30
    for threshold, pts in {1: 20, 7: 30, 30: 100, 60: 200, 100: 300}.items():
        if threshold == 7:
            if user.consecutive_login_days >= 7: total += pts
        elif user.total_login_days >= threshold: total += pts
    return total

@router.post("/{user_id}/claim-achievement-points", response_model=schema.UserResponse)
def claim_achievement_points(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    total_unlocked = calculate_total_achievement_points(current_user, db)
    already_claimed = current_user.claimed_achievement_points or 0
    if total_unlocked <= already_claimed: raise HTTPException(status_code=400, detail="目前沒有新的成就獎勵可以領取。")
    current_user.points += (total_unlocked - already_claimed)
    current_user.claimed_achievement_points = total_unlocked
    db.commit(); db.refresh(current_user)
    return current_user

@router.get("/{user_id}/signin-status", response_model=schema.SignInStatusResponse)
def signin_status(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    today = datetime.now().date().isoformat()
    signed_today = (current_user.last_checkin_date == today)
    cycle_day = get_cycle_day(current_user.consecutive_login_days)
    rewards = []
    for d in range(1, 8):
        rewards.append({
            "day": d,
            "points": SIGNIN_REWARDS.get(d, 0),
            "checked": d <= cycle_day and (signed_today or d < cycle_day)
        })
    return {
        "user_id": current_user.id,
        "points": current_user.points,
        "last_login_date": current_user.last_login_date,
        "last_checkin_date": current_user.last_checkin_date,
        "consecutive_login_days": current_user.consecutive_login_days,
        "cycle_day": cycle_day,
        "signed_today": signed_today,
        "rewards": rewards,
    }


@router.post("/{user_id}/signin", response_model=schema.SignInResponse)
def signin(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    today_date = datetime.now().date()
    today = today_date.isoformat()
    yesterday = (today_date - timedelta(days=1)).isoformat()
    if current_user.last_checkin_date == today:
        raise HTTPException(status_code=400, detail="Already signed today")
    if current_user.last_checkin_date == yesterday:
        current_user.consecutive_login_days = (current_user.consecutive_login_days or 0) + 1
    else:
        current_user.consecutive_login_days = 1
    current_user.total_login_days = (current_user.total_login_days or 0) + 1
    current_user.last_checkin_date = today
    cycle_day = get_cycle_day(current_user.consecutive_login_days)
    points_awarded = SIGNIN_REWARDS.get(cycle_day, 0)
    current_user.points = (current_user.points or 0) + points_awarded
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "user_id": current_user.id,
        "points_awarded": points_awarded,
        "points_total": current_user.points,
        "consecutive_login_days": current_user.consecutive_login_days,
        "cycle_day": cycle_day,
        "last_login_date": current_user.last_login_date,
        "last_checkin_date": current_user.last_checkin_date,
    }

@router.get("/{user_id}", response_model=schema.UserResponse)
def read_user(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    return current_user

@router.get("/{user_id}/recharge-records")
def get_user_recharge_records(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    records = db.query(models.RechargeRecord).filter(models.RechargeRecord.user_id == user_id).order_by(models.RechargeRecord.id.desc()).all()
    return records

@router.put("/{user_id}", response_model=schema.UserResponse)
def update_user(user_id: int, payload: schema.UserUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    current_user.name = payload.name; current_user.email = payload.email
    if payload.password: current_user.password = auth_schemas.hash_password(payload.password)
    if payload.current_quiz_draft is not None: current_user.current_quiz_draft = payload.current_quiz_draft
    db.commit(); db.refresh(current_user)
    return current_user

@router.get("/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id: raise HTTPException(status_code=403, detail="Forbidden")
    
    results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    v_c = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    d_c = db.query(models.Document).filter(models.Document.user_id == user_id).count()
    
    v_ana = db.query(models.Video).filter(models.Video.user_id == user_id, models.Video.outline != None).count()
    d_ana = db.query(models.Document).filter(models.Document.user_id == user_id, models.Document.outline != None).count()
    
    return schema.UserStatsResponse(
        video_count=v_c + d_c, 
        analyzed_video_count=v_ana + d_ana, 
        total_questions_count=sum(r.total_questions for r in results), 
        remaining_points=current_user.points, 
        completed_quizzes=len(results), 
        average_accuracy=round(sum(r.score for r in results)/len(results)) if results else 0
    )
