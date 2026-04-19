from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import database

app = FastAPI()

@app.on_event("startup")
def startup():
    # 啟動時自動建立資料表 (生產環境建議改用 Alembic 做遷移)
    models.Base.metadata.create_all(bind=database.engine)

@app.get("/users/{user_id}")
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
