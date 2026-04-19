from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

import database
import models

app = FastAPI()

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int

    class Config:
        orm_mode = True

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
        orm_mode = True

@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        try:
            user = db.query(models.User).filter(models.User.id == 1).first()
        except ProgrammingError:
            db.rollback()
            models.Base.metadata.drop_all(bind=database.engine)
            models.Base.metadata.create_all(bind=database.engine)
            user = None

        if user is None:
            user = models.User(
                id=1,
                name="wei",
                email="wei@gmail.com",
                password="password",
                uid="UID-20260419",
                points=10000,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

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
        user.password = payload.password
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
