# backend/main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.services.supabase_client import supabase
from app.services.document_processor import process_single_document
from app.models.schemas import DocumentResponse, DocumentListResponse, ProcessResponse
import asyncio
import os
import mimetypes
import uuid
from datetime import datetime
from typing import List, Optional
from postgrest.exceptions import APIError
import traceback
from app.api import upload, documents, chat

app = FastAPI(
    title="PDF Vectorization API",
    description="PDF 문서 업로드, 처리 및 벡터화 API",
    version="1.0.0"
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

# CORS 설정 (React 앱에서 API 호출을 위해)
# CORS 설정 (더 관대하게 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "*"  # 개발 환경에서만 사용
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------- 백그라운드 처리 함수 -------------------
async def process_pending_documents_task():
    """
    'pending' 상태의 문서를 찾아 처리하는 백그라운드 작업
    """
    print("--- 'pending' 문서 처리 작업 시작 ---")
    try:
        response = supabase.from_('documents').select('*').eq('status', 'pending').execute()
        pending_documents = response.data

        if not pending_documents:
            print("처리할 'pending' 상태 문서가 없습니다.")
            return

        print(f"처리할 'pending' 문서 {len(pending_documents)}개 발견.")

        for doc in pending_documents:
            document_id = doc['id']
            filename = doc['filename']
            url = doc['url']
            await process_single_document(document_id, filename, url)

    except Exception as e:
        print(f"pending 문서 처리 작업 오류: {e}")
        traceback.print_exc()
    finally:
        print("--- 'pending' 문서 처리 작업 종료 ---")


# ------------------- API 엔드포인트 -------------------

@app.get("/")
async def read_root():
    """API 상태 확인"""
    return {
        "message": "PDF Vectorization Backend API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        # Supabase 연결 테스트
        response = supabase.from_('documents').select('count', count='exact').limit(1).execute()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.post("/upload", response_model=ProcessResponse)
async def upload_pdf(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        auto_process: bool = Form(True)
):
    """
    PDF 파일 업로드 및 처리
    """
    try:
        # 파일 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

        # 파일 크기 확인 (50MB 제한)
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(
                status_code=400,
                detail=f"파일 크기가 너무 큽니다. 최대 50MB (현재: {file_size / (1024 * 1024):.1f}MB)"
            )

        # 고유한 파일명 생성
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_extension}"
        bucket_name = "pdf-documents"

        print(f"📤 파일 업로드 시작: {file.filename} -> {unique_filename}")

        # Supabase Storage에 업로드
        try:
            upload_response = supabase.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": "application/pdf"}
            )
            print(f"✅ Storage 업로드 성공: {upload_response}")
        except Exception as upload_error:
            raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(upload_error)}")

        # 공개 URL 생성
        try:
            supabase_file_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            print(f"🔗 공개 URL: {supabase_file_url}")
        except Exception:
            supabase_file_url = f"{supabase.url}/storage/v1/object/public/{bucket_name}/{unique_filename}"

        # DB에 메타데이터 저장 (현재 테이블 스키마에 맞게 수정)
        document_id = str(uuid.uuid4())

        try:
            # 현재 테이블 스키마에 맞춰 저장 (file_size 제외)
            db_response = supabase.from_('documents').insert({
                'id': document_id,
                'filename': file.filename,
                'url': supabase_file_url,
                'status': 'pending'
                # created_at은 DEFAULT로 자동 설정됨
                # file_size는 테이블에 컬럼이 없으므로 제외
            }).execute()

            print(f"✅ DB 저장 성공: {document_id}")
            print(f"DB Response: {db_response}")

        except Exception as db_error:
            print(f"❌ DB 저장 실패: {db_error}")
            print(f"DB Error Details: {type(db_error).__name__}: {str(db_error)}")

            # Storage에서 업로드된 파일 삭제 (정리)
            try:
                supabase.storage.from_(bucket_name).remove([unique_filename])
                print(f"🗑️ Storage 파일 정리 완료: {unique_filename}")
            except Exception as cleanup_error:
                print(f"⚠️ Storage 파일 정리 실패: {cleanup_error}")

            raise HTTPException(status_code=500, detail=f"메타데이터 저장 실패: {str(db_error)}")

        # 자동 처리 옵션이 켜져있으면 백그라운드에서 처리
        if auto_process:
            background_tasks.add_task(
                process_single_document,
                document_id,
                file.filename,
                supabase_file_url
            )

        return ProcessResponse(
            status="success",
            message="파일 업로드 완료" + (" 및 처리 시작" if auto_process else ""),
            document_id=document_id,
            filename=file.filename,
            file_size=file_size,
            processing=auto_process
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 업로드 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"업로드 처리 중 오류: {str(e)}")


# 새로 추가: 업로드 상태 확인 API
@app.get("/upload/status/{document_id}")
async def get_upload_status(document_id: str):
    """
    업로드 상태 확인
    """
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        doc = response.data[0]
        return {
            "status": doc['status'],
            "document_id": document_id,
            "filename": doc['filename'],
            "error_message": doc.get('error_message')  # 테이블에 없으면 None 반환
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents", response_model=DocumentListResponse)
async def get_documents(
        limit: int = 20,
        status: Optional[str] = None,
        page: int = 1
):
    """
    문서 목록 조회 (페이지네이션 지원)
    """
    try:
        offset = (page - 1) * limit

        query = supabase.from_('documents').select('*').order('created_at', desc=True)

        if status:
            query = query.eq('status', status)

        response = query.range(offset, offset + limit - 1).execute()

        # 전체 개수 조회
        count_query = supabase.from_('documents').select('count', count='exact')
        if status:
            count_query = count_query.eq('status', status)
        count_response = count_query.execute()

        return DocumentListResponse(
            status="success",
            data=response.data,
            count=len(response.data),
            total=count_response.count,
            page=page,
            limit=limit
        )

    except Exception as e:
        print(f"❌ 문서 목록 조회 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    특정 문서 상세 조회
    """
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        return DocumentResponse(
            status="success",
            data=response.data[0]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 문서 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{document_id}/process")
async def process_document(document_id: str, background_tasks: BackgroundTasks):
    """
    특정 문서 수동 처리 시작
    """
    try:
        # 문서 존재 확인
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        doc = response.data[0]

        if doc['status'] == 'processing':
            raise HTTPException(status_code=400, detail="이미 처리 중인 문서입니다.")

        if doc['status'] == 'completed':
            raise HTTPException(status_code=400, detail="이미 처리 완료된 문서입니다.")

        # 백그라운드에서 처리 시작
        background_tasks.add_task(
            process_single_document,
            document_id,
            doc['filename'],
            doc['url']
        )

        return {
            "status": "success",
            "message": "문서 처리가 시작되었습니다.",
            "document_id": document_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 문서 처리 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/process-pending")
async def trigger_process_pending(background_tasks: BackgroundTasks):
    """
    모든 pending 문서 처리 시작
    """
    background_tasks.add_task(process_pending_documents_task)
    return {
        "status": "success",
        "message": "Pending 문서 처리가 백그라운드에서 시작되었습니다."
    }


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    문서 삭제 (DB 및 Storage에서)
    """
    try:
        # 문서 정보 조회
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        doc = response.data[0]

        # Storage에서 파일 삭제 시도
        try:
            # URL에서 파일명 추출
            url_parts = doc['url'].split('/')
            filename = url_parts[-1]
            bucket_name = "pdf-documents"

            supabase.storage.from_(bucket_name).remove([filename])
            print(f"✅ Storage에서 파일 삭제: {filename}")
        except Exception as storage_error:
            print(f"⚠️ Storage 파일 삭제 실패: {storage_error}")
            # Storage 삭제 실패해도 DB에서는 삭제 진행

        # DB에서 삭제
        supabase.from_('documents').delete().eq('id', document_id).execute()

        return {
            "status": "success",
            "message": "문서가 삭제되었습니다.",
            "document_id": document_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 문서 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"❌ 전역 예외 발생: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "서버 내부 오류가 발생했습니다.",
            "detail": str(exc) if os.getenv("DEBUG") else "Internal server error"
        }
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 FastAPI 서버 시작...")
    print("📋 API 문서: http://127.0.0.1:8000/docs")
    print("🔗 API 엔드포인트: http://127.0.0.1:8000")
    print("💾 업로드 API: POST http://127.0.0.1:8000/upload")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,  # 개발 모드
        log_level="info"
    )