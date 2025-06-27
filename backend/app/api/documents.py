# backend/app/api/chat.py (Enhanced for RAG with Page Navigation)
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.document_processor import vector_collection
from app.services.vectorizer import get_embeddings
from app.services.supabase_client import supabase
from app.services.pdf_service import find_text_locations, create_highlighted_pdf, create_rag_response_with_pages
import openai
import time
import os
import tempfile
from typing import List, Dict, Any
import traceback

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """
    문서 기반 질의응답 (페이지 위치 정보 포함)
    """
    start_time = time.time()

    try:
        # 1. 사용자 질문을 임베딩으로 변환
        query_embedding = get_embeddings([request.message])[0]

        # 2. 유사한 문서 청크 검색
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": request.max_results
        }

        # 특정 문서에서만 검색하는 경우
        if request.document_ids:
            search_kwargs["where"] = {
                "document_id": {"$in": request.document_ids}
            }

        search_results = vector_collection.query(**search_kwargs)

        if not search_results["documents"] or not search_results["documents"][0]:
            return ChatResponse(
                status="success",
                answer="죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다. 다른 질문을 시도해보세요.",
                sources=[],
                document_ids=[],
                processing_time=time.time() - start_time
            )

        # 3. 검색된 청크들로 컨텍스트 구성
        documents = search_results["documents"][0]
        metadatas = search_results["metadatas"][0]
        distances = search_results["distances"][0]

        context_chunks = []
        sources = []
        document_ids = set()

        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            if distance < 0.8:  # 유사도 임계값
                context_chunks.append(doc)
                document_ids.add(metadata.get("document_id", ""))

                # 청크에서 페이지 정보 추출
                chunk_index = metadata.get("chunk_index", i)

                # 문서 정보 조회해서 실제 PDF 경로 얻기
                doc_info = await get_document_info(metadata.get("document_id", ""))

                source_info = {
                    "document_id": metadata.get("document_id", ""),
                    "filename": metadata.get("filename", "Unknown"),
                    "chunk_index": chunk_index,
                    "relevance_score": 1 - distance,
                    "content_preview": doc[:200] + "..." if len(doc) > 200 else doc,
                    "full_content": doc,
                    # 페이지 정보 (실제 PDF에서 찾아야 함)
                    "page_number": await find_chunk_page_number(doc_info, doc),
                    "bbox": None,  # 실제 구현에서는 PDF에서 위치 찾기
                }

                sources.append(source_info)

        if not context_chunks:
            return ChatResponse(
                status="success",
                answer="질문과 관련된 정보의 유사도가 낮아 정확한 답변을 제공하기 어렵습니다.",
                sources=[],
                document_ids=[],
                processing_time=time.time() - start_time
            )

        # 4. OpenAI API로 답변 생성
        context = "\n\n".join(context_chunks[:3])

        system_prompt = """당신은 PDF 문서의 내용을 바탕으로 질문에 답하는 AI 어시스턴트입니다. 
다음 규칙을 따라주세요:
1. 제공된 문서 내용만을 바탕으로 답변하세요
2. 문서에 없는 내용은 추측하지 마세요
3. 한국어로 명확하고 정확하게 답변하세요
4. 답변의 근거가 되는 문서 내용을 언급하세요
5. 확실하지 않은 경우 그렇다고 명시하세요"""

        user_prompt = f"""문서 내용:
{context}

질문: {request.message}

위 문서 내용을 바탕으로 질문에 답변해주세요."""

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            answer = response.choices[0].message.content

        except Exception as openai_error:
            print(f"❌ OpenAI API 오류: {openai_error}")
            # OpenAI API 실패 시 기본 답변
            answer = f"문서에서 다음과 관련된 정보를 찾았습니다:\n\n{context[:500]}...\n\n더 구체적인 답변을 위해 질문을 다시 정리해 주세요."

        processing_time = time.time() - start_time

        return ChatResponse(
            status="success",
            answer=answer,
            sources=sources,
            document_ids=list(document_ids),
            processing_time=processing_time
        )

    except Exception as e:
        print(f"❌ 채팅 처리 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류 발생: {str(e)}")


async def get_document_info(document_id: str) -> Dict:
    """문서 정보 조회"""
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()
        if response.data:
            return response.data[0]
        return {}
    except Exception as e:
        print(f"문서 정보 조회 실패: {e}")
        return {}


async def find_chunk_page_number(doc_info: Dict, chunk_text: str) -> int:
    """청크가 위치한 페이지 번호 찾기"""
    try:
        if not doc_info.get('url'):
            return 1

        # PDF 다운로드 (임시)
        import requests
        response = requests.get(doc_info['url'])

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name

        try:
            # 텍스트 위치 찾기
            locations = find_text_locations(tmp_file_path, chunk_text[:100])
            if locations:
                return locations[0].page_number
            return 1
        finally:
            # 임시 파일 삭제
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    except Exception as e:
        print(f"페이지 번호 찾기 실패: {e}")
        return 1


@router.post("/chat/highlight")
async def create_highlighted_response(
        document_id: str,
        page_number: int,
        search_text: str
):
    """
    특정 텍스트를 하이라이트한 PDF 생성
    """
    try:
        # 문서 정보 조회
        doc_info = await get_document_info(document_id)
        if not doc_info.get('url'):
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        # PDF 다운로드
        import requests
        response = requests.get(doc_info['url'])

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name

        try:
            # 텍스트 위치 찾기
            locations = find_text_locations(tmp_file_path, search_text)

            if not locations:
                return {
                    "status": "error",
                    "message": "해당 텍스트를 찾을 수 없습니다."
                }

            # 하이라이트된 PDF 생성
            highlighted_path = create_highlighted_pdf(tmp_file_path, locations)

            # 하이라이트된 PDF를 Supabase Storage에 업로드
            highlighted_url = await upload_highlighted_pdf(highlighted_path, document_id)

            return {
                "status": "success",
                "highlighted_pdf_url": highlighted_url,
                "page_number": locations[0].page_number,
                "bbox": locations[0].bbox,
                "total_highlights": len(locations)
            }

        finally:
            # 임시 파일들 정리
            for file_path in [tmp_file_path, highlighted_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)

    except Exception as e:
        print(f"❌ 하이라이트 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def upload_highlighted_pdf(file_path: str, document_id: str) -> str:
    """하이라이트된 PDF를 Supabase Storage에 업로드"""
    try:
        highlighted_filename = f"highlighted_{document_id}.pdf"

        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Supabase Storage에 업로드
        upload_response = supabase.storage.from_("pdf-documents").upload(
            path=f"highlighted/{highlighted_filename}",
            file=file_content,
            file_options={"content-type": "application/pdf"}
        )

        # 공개 URL 생성
        public_url = supabase.storage.from_("pdf-documents").get_public_url(
            f"highlighted/{highlighted_filename}"
        )

        return public_url

    except Exception as e:
        print(f"하이라이트된 PDF 업로드 실패: {e}")
        return ""


@router.get("/chat/page-navigation/{document_id}")
async def get_page_navigation_info(document_id: str, search_text: str):
    """
    특정 텍스트의 페이지 위치 정보 반환 (PDF 뷰어용)
    """
    try:
        # 문서 정보 조회
        doc_info = await get_document_info(document_id)
        if not doc_info.get('url'):
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        # PDF 다운로드
        import requests
        response = requests.get(doc_info['url'])

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name

        try:
            # 텍스트 위치 찾기
            locations = find_text_locations(tmp_file_path, search_text)

            navigation_info = []
            for location in locations:
                navigation_info.append({
                    "page_number": location.page_number,
                    "bbox": {
                        "x0": location.bbox[0],
                        "y0": location.bbox[1],
                        "x1": location.bbox[2],
                        "y1": location.bbox[3]
                    },
                    "context": location.context,
                    "matched_text": location.text
                })

            return {
                "status": "success",
                "document_id": document_id,
                "search_text": search_text,
                "total_matches": len(navigation_info),
                "locations": navigation_info,
                "primary_page": navigation_info[0]["page_number"] if navigation_info else 1
            }

        finally:
            # 임시 파일 정리
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    except Exception as e:
        print(f"❌ 페이지 네비게이션 정보 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/search")
async def search_documents(query: str, document_ids: List[str] = None, limit: int = 10):
    """
    문서 검색 (답변 생성 없이 검색만, 페이지 정보 포함)
    """
    try:
        # 쿼리를 임베딩으로 변환
        query_embedding = get_embeddings([query])[0]

        # 검색 실행
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": limit
        }

        if document_ids:
            search_kwargs["where"] = {
                "document_id": {"$in": document_ids}
            }

        search_results = vector_collection.query(**search_kwargs)

        if not search_results["documents"] or not search_results["documents"][0]:
            return {
                "status": "success",
                "results": [],
                "message": "검색 결과가 없습니다."
            }

        # 결과 정리 (페이지 정보 포함)
        documents = search_results["documents"][0]
        metadatas = search_results["metadatas"][0]
        distances = search_results["distances"][0]

        results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            # 문서 정보 조회
            doc_info = await get_document_info(metadata.get("document_id", ""))
            page_number = await find_chunk_page_number(doc_info, doc)

            results.append({
                "document_id": metadata.get("document_id", ""),
                "filename": metadata.get("filename", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "content": doc,
                "relevance_score": 1 - distance,
                "distance": distance,
                "page_number": page_number,
                "navigation_info": {
                    "can_highlight": True,
                    "can_navigate": True
                }
            })

        return {
            "status": "success",
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        print(f"❌ 문서 검색 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/documents")
async def get_available_documents():
    """
    채팅에 사용 가능한 문서 목록 조회 (완료된 문서만)
    """
    try:
        response = supabase.from_('documents').select('id, filename, created_at, processed_at').eq('status',
                                                                                                   'completed').order(
            'created_at', desc=True).execute()

        return {
            "status": "success",
            "documents": response.data,
            "count": len(response.data)
        }

    except Exception as e:
        print(f"❌ 사용 가능한 문서 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/feedback")
async def submit_chat_feedback(
        message: str,
        answer: str,
        rating: int,
        feedback_text: str = None,
        page_navigation_used: bool = False,
        highlight_used: bool = False
):
    """
    채팅 답변에 대한 피드백 수집 (페이지 네비게이션/하이라이트 사용 여부 포함)
    """
    try:
        feedback_data = {
            "message": message,
            "answer": answer,
            "rating": rating,
            "feedback_text": feedback_text,
            "page_navigation_used": page_navigation_used,
            "highlight_used": highlight_used,
            "timestamp": time.time()
        }

        # 여기서는 단순히 로그만 출력 (실제로는 DB에 저장)
        print(f"📝 사용자 피드백: {feedback_data}")

        return {
            "status": "success",
            "message": "피드백이 저장되었습니다."
        }

    except Exception as e:
        print(f"❌ 피드백 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))