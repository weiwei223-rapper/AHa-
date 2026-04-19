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
    return {"id": user.id, "email": user.email, "name": user.name}