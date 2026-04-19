from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VideoCreate(BaseModel):
    video_link: str

class VideoResponse(BaseModel):
    id: int
    video_link: str
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True   # Pydantic v2