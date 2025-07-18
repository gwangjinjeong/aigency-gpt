# backend/app/api/upload.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.services.supabase_client import supabase
from app.services.document_processor import process_single_document
from app.models.schemas import ProcessResponse
from app.core.config import settings
import uuid
import os
from datetime import datetime
import traceback

router = APIRouter()


@router.post("/upload", response_model=ProcessResponse)
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

        # 파일 크기 확인
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"파일 크기가 너무 큽니다. 최대 {settings.MAX_FILE_SIZE // (1024 * 1024)}MB (현재: {file_size / (1024 * 1024):.1f}MB)"
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

        # 고유한 파일명 생성
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_extension}"

        print(f"📤 파일 업로드 시작: {file.filename} -> {unique_filename}")

        # Supabase Storage에 업로드
        try:
            upload_response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": "application/pdf"}
            )
            print(f"✅ Storage 업로드 성공: {upload_response}")
        except Exception as upload_error:
            print(f"❌ Storage 업로드 실패: {upload_error}")
            raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(upload_error)}")

        # 공개 URL 생성
        try:
            # .get_public_url()의 결과에서 .data['publicUrl']을 직접 사용
            supabase_file_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(unique_filename).data['publicUrl']

            if not supabase_file_url:
                raise ValueError("Supabase에서 유효한 공개 URL을 받지 못했습니다.")

            print(f"🔗 공개 URL: {supabase_file_url}")
        except Exception as e:
            print(f"⚠️ get_public_url 실패 ({e}), 수동으로 URL 구성")
            supabase_file_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/{unique_filename}"

        # DB에 메타데이터 저장
        document_id = str(uuid.uuid4())

        try:
            db_response = supabase.from_('documents').insert([
                {
                    'id': document_id,
                    'filename': file.filename,
                    'url': supabase_file_url,
                    'status': 'pending'
                }
            ]).execute()
            print(f"✅ DB 저장 성공: {document_id}")
        except Exception as db_error:
            print(f"❌ DB 저장 실패: {db_error}")
            # 롤백: Storage에서 업로드된 파일 삭제
            try:
                supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([unique_filename])
                print(f"🗑️ Storage 파일 롤백 완료: {unique_filename}")
            except Exception as cleanup_error:
                print(f"⚠️ Storage 파일 롤백 실패: {cleanup_error}")
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


@router.get("/upload/status/{document_id}")
async def get_upload_status(document_id: str):
    """
    업로드 및 처리 상태 확인
    """
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        document = response.data[0]

        return {
            "status": "success",
            "document_id": document_id,
            "filename": document['filename'],
            "processing_status": document['status'],
            "created_at": document['created_at'],
            "processed_at": document.get('processed_at'),
            "url": document.get('url')
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/retry/{document_id}")
async def retry_processing(document_id: str, background_tasks: BackgroundTasks):
    """
    실패한 문서 재처리
    """
    try:
        # 문서 존재 확인
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        document = response.data[0]

        if document['status'] == 'completed':
            raise HTTPException(status_code=400, detail="이미 처리 완료된 문서입니다.")

        if document['status'] == 'processing':
            raise HTTPException(status_code=400, detail="이미 처리 중인 문서입니다.")

        # 상태를 pending으로 변경
        supabase.from_('documents').update({
            'status': 'pending',
            'processed_at': None
        }).eq('id', document_id).execute()

        # 백그라운드에서 재처리 시작
        background_tasks.add_task(
            process_single_document,
            document_id,
            document['filename'],
            document['url']
        )

        return {
            "status": "success",
            "message": "문서 재처리가 시작되었습니다.",
            "document_id": document_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 재처리 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))