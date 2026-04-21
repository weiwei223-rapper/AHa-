from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import bcrypt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

import database
import models

# Password hashing functions - define early so they can be used in startup
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - create tables and initial data
    try:
        models.Base.metadata.create_all(bind=database.engine)
        # Create initial user if not exists
        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == 1).first()
            if user is None:
                hashed_pwd = hash_password("password")
                user = models.User(
                    id=1,
                    name="wei",
                    email="wei@gmail.com",
                    password=hashed_pwd,
                    uid="UID-20260419",
                    points=10000,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print("Initial user created")
        finally:
            db.close()
    except Exception as e:
        print(f"Error during startup: {e}")
    yield

    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None

class RechargeRequest(BaseModel):
    points: int
    price: int

class RechargeRecordResponse(BaseModel):
    date: str
    order_id: str
    amount: int

    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    user: UserResponse
    message: str

@app.post("/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    # Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="該電子郵件已被使用")
    
    # Generate UID with current date
    uid = f"UID-{datetime.utcnow():%Y%m%d%H%M}"
    
    # Hash the password
    hashed_password = hash_password(payload.password)
    
    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
        uid=uid,
        points=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="電子郵件或密碼錯誤")
    
    # Verify the password using bcrypt
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="電子郵件或密碼錯誤")
    
    return {
        "user": user,
        "message": f"歡迎回來，{user.name}！"
    }

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    user.name = payload.name
    user.email = payload.email
    if payload.password:
        # Hash the password before updating
        user.password = hash_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/users/{user_id}/recharge-records", response_model=List[RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    records = (
        db.query(models.RechargeRecord)
        .filter(models.RechargeRecord.user_id == user_id)
        .order_by(models.RechargeRecord.id.desc())
        .all()
    )
    return records

@app.post("/users/{user_id}/recharge", response_model=RechargeRecordResponse)
def recharge_user(user_id: int, payload: RechargeRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    order_id = f"A{datetime.utcnow():%Y%m%d%H%M%S}"
    record = models.RechargeRecord(
        user_id=user.id,
        date=datetime.utcnow().strftime("%Y/%m/%d"),
        order_id=order_id,
        amount=payload.price,
    )
    user.points += payload.points
    db.add(record)
    db.add(user)
    db.commit()
    db.refresh(record)
    db.refresh(user)
    return record
