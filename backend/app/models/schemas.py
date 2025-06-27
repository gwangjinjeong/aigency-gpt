# backend/app/models/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class DocumentBase(BaseModel):
    filename: str
    url: Optional[str] = None
    status: str = 'pending'
    # file_size와 error_message는 DB 스키마에 없음

class DocumentCreate(DocumentBase):
    id: str
    created_at: datetime

class Document(DocumentBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    chunk_count: Optional[int] = None
    processing_time: Optional[float] = None

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    status: str
    data: Document

class DocumentListResponse(BaseModel):
    status: str
    data: List[Document]
    count: int
    total: int
    page: int
    limit: int

class ProcessResponse(BaseModel):
    status: str
    message: str
    document_id: str
    filename: str
    file_size: int
    processing: bool = False

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[List[str]] = None  # 특정 문서에서만 검색
    max_results: int = 5

class ChatResponse(BaseModel):
    status: str
    answer: str
    sources: List[Dict[str, Any]]  # 출처 정보 (페이지, 위치 등)
    document_ids: List[str]
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str
    message: str
    detail: Optional[str] = None
    timestamp: Optional[datetime] = None