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
from app.api import upload, chat

app = FastAPI(
    title="PDF Vectorization API",
    description="PDF 문서 업로드, 처리 및 벡터화 API",
    version="1.0.0"
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
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

# --- 관리자용 엔드포인트 ---
from app.services import document_processor
import traceback
from fastapi import HTTPException
import shutil
import os
import chromadb

@app.post("/admin/reset-vector-db")
async def reset_vector_db():
    """
    Supabase Storage, DB, 로컬 벡터 DB, PDF 캐시를 포함한 모든 데이터를 삭제하고 초기화합니다.
    경고: 모든 데이터가 영구적으로 삭제됩니다.
    """
    print("--- ⚠️ 전체 시스템 데이터 초기화 시작... ---")
    try:
        # 1. Supabase에서 모든 문서 정보 가져오기
        print("--- Supabase에서 모든 문서 목록 조회 중... ---")
        docs_response = document_processor.supabase.from_('documents').select('id, url').execute()
        all_documents = docs_response.data

        if all_documents:
            # 2. Supabase Storage에서 모든 파일 삭제
            print(f"--- Supabase Storage에서 {len(all_documents)}개 파일 삭제 중... ---")
            file_paths_to_delete = []
            for doc in all_documents:
                # URL에서 파일 경로 추출 (더 안정적인 방식)
                try:
                    file_path = doc['url'].split(f"/{document_processor.settings.SUPABASE_BUCKET_NAME}/")[-1]
                    file_paths_to_delete.append(file_path)
                except Exception as e:
                    print(f"⚠️ 파일 경로 추출 실패 (문서 ID: {doc['id']}): {e}")
            
            if file_paths_to_delete:
                document_processor.supabase.storage.from_(document_processor.settings.SUPABASE_BUCKET_NAME).remove(file_paths_to_delete)
                print("✅ Supabase Storage 파일 삭제 완료.")

            # 3. Supabase DB에서 모든 레코드 삭제
            print("--- Supabase DB에서 모든 레코드 삭제 중... ---")
            document_processor.supabase.from_('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute() # 모든 레코드 삭제
            print("✅ Supabase DB 레코드 삭제 완료.")
        else:
            print("--- Supabase에 삭제할 문서가 없습니다. ---")

        # 4. 로컬 ChromaDB 폴더 삭제
        chroma_db_path = "./chroma_db"
        if os.path.exists(chroma_db_path):
            shutil.rmtree(chroma_db_path)
            print(f"✅ '{chroma_db_path}' 폴더 삭제 완료.")

        # 5. 로컬 PDF 캐시 폴더 삭제
        pdf_cache_path = "./pdf_cache"
        if os.path.exists(pdf_cache_path):
            shutil.rmtree(pdf_cache_path)
            print(f"✅ '{pdf_cache_path}' 폴더 삭제 완료.")

        # 6. 빈 폴더 재생성 및 ChromaDB 클라이언트 재초기화
        os.makedirs(chroma_db_path, exist_ok=True)
        os.makedirs(pdf_cache_path, exist_ok=True)
        print("--- ChromaDB 클라이언트 및 컬렉션 재초기화 중... ---")
        new_client = chromadb.PersistentClient(path=chroma_db_path)
        new_collection = new_client.get_or_create_collection(name=document_processor.collection_name)
        document_processor.chroma_client = new_client
        document_processor.vector_collection = new_collection
        
        print("✅ 모든 데이터가 성공적으로 초기화되었습니다.")
        return {"status": "success", "message": "Supabase와 로컬 데이터가 모두 초기화되었습니다."}

    except Exception as e:
        print(f"❌ 전체 초기화 실패: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"전체 초기화 실패: {e}")



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