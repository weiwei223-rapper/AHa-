from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import sys
import os

# Ensure backend root is in path for absolute imports if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import database
import schema
import auth_schemas
from auth_utils import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=auth_schemas.LoginResponse)
def register_user(payload: auth_schemas.RegisterRequest, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first(): 
        raise HTTPException(status_code=400, detail="Email exists")
    new_user = models.User(name=payload.name, email=payload.email, password=auth_schemas.hash_password(payload.password), uid=f"UID-{datetime.now():%Y%m%d%H%M}", points=0)
    db.add(new_user); db.commit(); db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"user": new_user, "message": f"Welcome, {new_user.name}", "access_token": access_token}

@router.post("/login", response_model=auth_schemas.LoginResponse)
def login_user(payload: auth_schemas.LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth_schemas.verify_password(payload.password, user.password): 
        raise HTTPException(status_code=401, detail="Invalid email/password")
    today = datetime.now().date().isoformat()
    if user.last_login_date != today:
        if user.last_login_date == (datetime.now().date() - timedelta(days=1)).isoformat(): 
            user.consecutive_login_days += 1
        else: 
            user.consecutive_login_days = 1
        user.total_login_days += 1
        user.last_login_date = today
        db.commit()
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"user": user, "message": f"Welcome back, {user.name}", "access_token": access_token}

@router.post("/guest", response_model=auth_schemas.LoginResponse)
def guest_login(db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == 1).first()
    if not user:
        raise HTTPException(status_code=404, detail="Guest user not found")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"user": user, "message": "Logged in as guest", "access_token": access_token}
