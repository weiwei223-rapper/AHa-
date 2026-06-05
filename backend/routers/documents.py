import math
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import models
import database
import schema
import ai_analyzer
import learning_pipeline
from report_utils import process_error_report_task
from auth_utils import get_current_user

# --- Helper for PDF ---
try:
    import fitz  # PyMuPDF
except ImportError:
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = None

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("", response_model=schema.DocumentResponse)
async def upload_document(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅支援 PDF 檔案格式")
    try:
        content = await file.read()
        text_content = ""
        if fitz:
            try:
                with fitz.open(stream=content, filetype="pdf") as doc:
                    for page in doc:
                        text_content += page.get_text()
            except Exception as fe:
                raise ValueError(f"PDF 解析失敗: {str(fe)}")
        else:
            raise ValueError("伺服器尚未安裝 PDF 解析組件 (PyMuPDF)")
            
        if not text_content.strip():
            raise ValueError("無法從此 PDF 中提取文字內容。請確認該 PDF 並非純圖片掃描檔，或是具備可搜尋文字。")

        # 正規化文字內容以利比較 (移除多餘空白、換行)
        normalized_content = " ".join(text_content.split())
        
        # 檢查是否已存在相同名稱或內容的 PDF
        # 先抓出該使用者的所有文件進行比對 (避免大型 Text 欄位在不同 DB 上的比較差異)
        user_docs = db.query(models.Document).filter(models.Document.user_id == current_user.id).all()
        for d in user_docs:
            d_normalized = " ".join((d.content_text or "").split())
            if d.filename == file.filename or d_normalized == normalized_content:
                print(f"DEBUG: Duplicate document found. Filename match: {d.filename == file.filename}, Content match: {d_normalized == normalized_content}")
                raise HTTPException(status_code=400, detail="此影片已存在於您的教材庫中")

        title = file.filename.rsplit(".", 1)[0]
        if not ai_analyzer.is_python_related(title, text_content, content_type="文件"):
            raise HTTPException(status_code=400, detail="僅支援 Python 相關文件內容")

        doc_model = models.Document(
            filename=file.filename,
            title=title,
            content_text=text_content,
            user_id=current_user.id
        )
        db.add(doc_model)
        db.commit()
        db.refresh(doc_model)
        return doc_model
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[schema.DocumentResponse])
def get_documents(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    return db.query(models.Document).filter(models.Document.user_id == current_user.id).all()

@router.get("/{doc_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_document(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        outline, usage = learning_pipeline.generate_outline(doc.content_text, doc.title)
        pts = math.ceil(((usage.get("totalTokenCount", 0)) / 2000) * 100 / 10) * 10
        if current_user.points < pts: raise HTTPException(status_code=400, detail="點數不足")
        
        current_user.points -= pts
        db.add(models.UploadRecord(user_id=current_user.id, document_id=doc.id, consumed_points=pts))
        doc.outline = outline
        db.commit(); db.refresh(doc)
        return schema.VideoAnalysisResponse(
            video_id=doc.id, video_title=doc.title, transcript_source="pdf_extract",
            transcript_excerpt=doc.content_text[:1000], outline_markdown=outline,
            key_topics=learning_pipeline._parse_bullets(outline), retrieved_chunks=[],
            vector_backend="none", generated_at=datetime.utcnow(),
            token_usage=learning_pipeline._to_token_usage_schema(usage)
        )
    except Exception as e: 
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
def delete_document(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}

@router.post("/{doc_id}/report-error", response_model=schema.DocumentResponse)
def report_document_error(doc_id: int, payload: schema.ErrorReportRequest, background_tasks: BackgroundTasks, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id: raise HTTPException(status_code=403, detail="Forbidden")
    doc.error_report = payload.error_report
    db.commit(); db.refresh(doc)
    
    background_tasks.add_task(process_error_report_task, doc.id, "document", current_user.id)
    return doc
