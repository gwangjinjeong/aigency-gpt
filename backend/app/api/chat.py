# backend/app/routers/chat.py 에 추가할 엔드포인트

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import logging
from app.services.document_processor import get_document_pdf_path, search_similar_documents_with_pages
from app.services.pdf_service import find_text_locations, PDFProcessor
from app.services.supabase_client import supabase
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/page-navigation/{document_id}")
async def get_page_navigation(
        document_id: str,
        search_text: str = Query(..., description="검색할 텍스트")
):
    """
    특정 문서에서 텍스트를 검색하여 페이지 위치 정보를 반환합니다.
    """
    try:
        logger.info(f"페이지 네비게이션 요청: 문서 ID {document_id}, 검색어 '{search_text}'")

        # 1. 문서 존재 여부 확인
        try:
            doc_response = supabase.from_('documents').select('*').eq('id', document_id).execute()
            if not doc_response.data:
                logger.error(f"문서를 찾을 수 없음: {document_id}")
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

            document = doc_response.data[0]
            logger.info(f"문서 정보 확인: {document['filename']}")

        except Exception as db_error:
            logger.error(f"문서 조회 중 오류: {db_error}")
            raise HTTPException(status_code=500, detail="문서 조회 중 오류가 발생했습니다.")

        # 2. PDF 파일 경로 획득
        try:
            pdf_file_path = get_document_pdf_path(document_id)
            logger.info(f"PDF 파일 경로: {pdf_file_path}")

        except Exception as path_error:
            logger.error(f"PDF 파일 경로 획득 실패: {path_error}")
            raise HTTPException(status_code=500, detail="PDF 파일을 찾을 수 없습니다.")

        # 3. PDF에서 텍스트 위치 검색
        try:
            locations = find_text_locations(pdf_file_path, search_text)
            logger.info(f"텍스트 검색 결과: {len(locations)}개 위치 발견")

            if not locations:
                return {
                    "status": "success",
                    "message": "검색 결과가 없습니다.",
                    "document_id": document_id,
                    "search_text": search_text,
                    "locations": [],
                    "total_matches": 0
                }

            # 위치 정보를 API 응답 형식으로 변환
            location_results = []
            for i, location in enumerate(locations):
                location_data = {
                    "index": i,
                    "page_number": location.page_number,
                    "bbox": {
                        "x0": location.bbox[0],
                        "y0": location.bbox[1],
                        "x1": location.bbox[2],
                        "y1": location.bbox[3]
                    },
                    "matched_text": location.text,
                    "context": location.context,
                    "confidence": 1.0  # PyMuPDF 검색은 정확한 매치이므로 높은 신뢰도
                }
                location_results.append(location_data)

            return {
                "status": "success",
                "message": f"{len(locations)}개의 위치를 찾았습니다.",
                "document_id": document_id,
                "document_filename": document['filename'],
                "search_text": search_text,
                "locations": location_results,
                "total_matches": len(locations)
            }

        except Exception as search_error:
            logger.error(f"텍스트 검색 중 오류: {search_error}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="텍스트 검색 중 오류가 발생했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 페이지 네비게이션 정보 생성 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="페이지 네비게이션 정보 생성 중 오류가 발생했습니다.")


@router.post("/highlight")
async def create_highlight_pdf(
        request: Dict
):
    """
    특정 텍스트를 하이라이트한 PDF를 생성합니다.
    """
    try:
        document_id = request.get("document_id")
        search_text = request.get("search_text")
        page_number = request.get("page_number", 1)

        if not document_id or not search_text:
            raise HTTPException(status_code=400, detail="document_id와 search_text가 필요합니다.")

        logger.info(f"하이라이트 PDF 생성 요청: {document_id}, '{search_text}'")

        # 1. 문서 존재 여부 확인
        doc_response = supabase.from_('documents').select('*').eq('id', document_id).execute()
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        document = doc_response.data[0]

        # 2. PDF 파일 경로 획득
        try:
            pdf_file_path = get_document_pdf_path(document_id)
        except Exception as path_error:
            logger.error(f"PDF 파일 경로 획득 실패: {path_error}")
            raise HTTPException(status_code=500, detail="PDF 파일을 찾을 수 없습니다.")

        # 3. 텍스트 위치 찾기
        locations = find_text_locations(pdf_file_path, search_text)

        if not locations:
            return {
                "status": "failed",
                "message": "검색된 텍스트가 없어 하이라이트를 생성할 수 없습니다."
            }

        # 4. 하이라이트된 PDF 생성
        try:
            from app.services.pdf_service import create_highlighted_pdf
            import os
            import time

            # 하이라이트된 PDF 파일명 생성
            timestamp = int(time.time())
            highlighted_filename = f"{document_id}_highlighted_{timestamp}.pdf"
            highlighted_path = os.path.join("./pdf_cache", highlighted_filename)

            # 하이라이트 PDF 생성
            result_path = create_highlighted_pdf(pdf_file_path, locations, highlighted_path)

            if os.path.exists(result_path):
                # 공개 URL 생성 (실제 구현에서는 적절한 정적 파일 서빙 필요)
                highlighted_url = f"/static/pdf/{highlighted_filename}"

                return {
                    "status": "success",
                    "message": "하이라이트된 PDF가 생성되었습니다.",
                    "highlighted_pdf_url": highlighted_url,
                    "highlights_count": len(locations)
                }
            else:
                raise Exception("하이라이트된 PDF 파일 생성 실패")

        except Exception as highlight_error:
            logger.error(f"하이라이트 PDF 생성 실패: {highlight_error}")
            raise HTTPException(status_code=500, detail="하이라이트 PDF 생성 중 오류가 발생했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"하이라이트 생성 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="하이라이트 생성 중 오류가 발생했습니다.")


@router.get("/documents/{document_id}/pages")
async def get_document_pages(document_id: str):
    """
    문서의 페이지 정보를 조회합니다.
    """
    try:
        # 문서 존재 여부 확인
        doc_response = supabase.from_('documents').select('*').eq('id', document_id).execute()
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        document = doc_response.data[0]

        # PDF 파일에서 페이지 정보 추출
        try:
            pdf_file_path = get_document_pdf_path(document_id)

            # PDF 프로세서를 사용하여 메타데이터 추출
            pdf_processor = PDFProcessor()
            metadata_result = pdf_processor.extract_metadata(pdf_file_path)

            if metadata_result["status"] == "success":
                total_pages = metadata_result["document_info"]["page_count"]

                return {
                    "status": "success",
                    "document_id": document_id,
                    "filename": document["filename"],
                    "total_pages": total_pages,
                    "document_info": metadata_result["document_info"],
                    "pdf_metadata": metadata_result["pdf_metadata"]
                }
            else:
                raise Exception(metadata_result.get("error", "메타데이터 추출 실패"))

        except Exception as pdf_error:
            logger.error(f"PDF 페이지 정보 추출 실패: {pdf_error}")
            raise HTTPException(status_code=500, detail="PDF 페이지 정보를 가져올 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"페이지 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="페이지 정보 조회 중 오류가 발생했습니다.")


# 정적 파일 서빙을 위한 추가 라우터 (main.py에 추가)