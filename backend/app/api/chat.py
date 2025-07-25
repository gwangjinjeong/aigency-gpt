# backend/app/api/chat.py (Enhanced for RAG with Page Navigation & Cache Integration)
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import ChatRequest, ChatResponse
from app.services.document_processor import vector_collection, PDFFileManager, get_document_pdf_path
from app.services.vectorizer import get_embeddings
from app.services.supabase_client import supabase
from app.services.pdf_service import find_text_locations, create_highlighted_pdf, create_rag_response_with_pages
import openai
import time
import os
import tempfile
from typing import List, Dict, Any, Optional
import traceback

from app.services.query_rewriter import rewrite_query

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """
    문서 기반 질의응답 (페이지 위치 정보 포함, 캐시 활용)
    """
    start_time = time.time()

    try:
        # 1. 사용자 질문을 임베딩으로 변환 (질문 재구성 제거)
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

        # 3. 검색된 청크들로 컨텍스트 구성 및 소스 정보 보강
        documents = search_results["documents"][0]
        metadatas = search_results["metadatas"][0]
        distances = search_results["distances"][0]

        context_chunks = []
        sources = []
        document_ids = set()
        
        # 문서 정보를 한 번에 조회하기 위한 준비
        referenced_doc_ids = list(set([meta.get("document_id") for meta in metadatas if meta.get("document_id")]))
        document_info_map = {}
        if referenced_doc_ids:
            try:
                doc_infos_response = supabase.from_('documents').select('id, url, filename').in_('id', referenced_doc_ids).execute()
                for doc_info in doc_infos_response.data:
                    document_info_map[doc_info['id']] = doc_info
            except Exception as db_error:
                print(f"❌ 참조된 문서 정보 조회 실패: {db_error}")


        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            if distance < 0.8:  # 유사도 임계값
                context_chunks.append(doc)
                document_id = metadata.get("document_id", "")
                document_ids.add(document_id)

                # 메타데이터에서 페이지 정보 직접 추출 (캐시 활용)
                start_page = metadata.get("start_page", 1)
                end_page = metadata.get("end_page", 1)
                chunk_index = metadata.get("chunk_index", i)

                # 조회된 문서 정보맵에서 URL과 파일명 가져오기
                doc_info = document_info_map.get(document_id, {})
                
                source_info = {
                    "document_id": document_id,
                    "filename": doc_info.get("filename", "Unknown"),
                    "url": doc_info.get("url", ""),  # URL 추가
                    "chunk_index": chunk_index,
                    "relevance_score": 1 - distance,
                    "content_preview": doc[:200] + "..." if len(doc) > 200 else doc,
                    "full_content": doc,
                    "page_number": start_page,
                    "end_page": end_page,
                    "bbox": None,  # 필요시 실시간으로 계산
                    "chunk_hash": metadata.get("chunk_hash", ""),
                    "char_count": metadata.get("char_count", len(doc))
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

        # 대화 기록을 포함하여 프롬프트 재구성
        messages = [
            {"role": "system", "content": """Your Role: You are a 'Bank Product Specialist AI'. Your sole mission is to provide accurate and reliable information about financial products based only on the provided 'context' document. NEVER guess or use external knowledge.
            Core Principles**
            1.  Respond in Korean**: All final answers to the user **must be written in clear and natural Korean.
            2.  Strictly Grounded Answering**: All answers must be based strictly on the information stated in the 'context'
            3.  Accuracy**: You must convey all numbers, conditions, and names with perfect accuracy.
            4.  Professional Tone**: Regardless of the user's tone, you must always maintain a neutral, objective, and expert tone. Do not recommend products or offer personal opinions.
            
            Guide by Question Type
            1. Fact-Based Questions
            When the user asks for specific information (loan limit, interest rate, term, etc.), deliver the facts from the 'context' concisely and without distortion.
            - User Question: "우리은행 네이버 스마트스토어 대출의 상환 방식은 무엇인가요?"
            - 'context': '만기일시상환, 원(리)금균등분할상환, 마이너스통장'
            - Correct Answer: "만기일시상환, 원리금균등분할상환, 원금균등분할상환, 마이너스통장 방식 중에서 선택 가능합니다."
            
            2. Inferential Questions
            If the 'context' doesn't state something directly but a logical inference is needed, answer using cautious phrasing like **'~일 수 있습니다' (it may be...), '~할 가능성이 있습니다' (it's possible that...), or '~에 따라 달라질 수 있습니다' (it can depend on...).
            - User Question**: "스마트스토어 개설 후 1개월 된 셀러는 이 상품을 신청할 수 있나요?"
            - 'context': '사업자등록 후 3개월 이상 경과해야 함'
            - Correct Answer**: "아니요, 제공된 정보에 따르면 사업자등록 후 3개월 이상 경과해야 하므로 신청이 어려울 수 있습니다."
            
            3. Fact-Checking & Correction Questions
            If the user's question contains information that contradicts the `context`, NEVER agree with them. Politely correct the misinformation based on the facts in the 'context'
            - User Question: "우리은행 네이버 스마트스토어 대출은 부동산 담보가 필요하다고 들었어요
            - 'context': '무담보 신용대출'
            - Correct Answer: "아닙니다. 확인된 정보에 따르면 해당 상품은 부동산 담보가 필요 없는 무담보 신용대출입니다."
            
            4. Multi-Part Questions
            If the user asks multiple things at once, break down the query and answer each part clearly and sequentially.
            - User Question: "제가 스마트스토어 운영 4개월차이고, CB 등급은 3등급입니다. 대출 가능할까요?"
            - 'context': '3개월 이상 경과', 'CB 4(+) 이하 신규 불가'
            - Correct Answer**: "네, 문의하신 조건(스마트스토어 운영 4개월, CB 3등급)은 상품의 기본 자격 요건을 충족하므로 신청 가능합니다."
            
            5. Eligibility & Informal Questions
            When a user asks about their eligibility using an informal tone, maintain a professional tone while answering clearly and firmly. If they do not qualify, you must politely but explicitly explain the reason for rejection based on the `context`.
            - User Question: "야 나 무직이거든? 우리주거래 신용대출 받을 수 있어?"
            - 'context': '(상품 정보에 '직장인 대상 신용대출' 명시)'
            - Correct Answer: "문의주신 우리주거래 신용대출은 직장인 대상 상품으로, 현재 직업이 없으시다면 해당 상품의 이용은 어렵습니다."
"""}
        ]

        if request.history:
            for message in request.history:
                messages.append({"role": message.role, "content": message.content})

        user_prompt = f"""**대화 기록:**
{request.history if request.history else '이전 대화 없음'}

**새로운 문서 내용:**
{context}

**사용자 질문:** {request.message}

---
위 대화 기록과 새로운 문서 내용을 종합하여 사용자 질문에 답변해주세요."""
        
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
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


# 🔥 수정된 하이라이트 엔드포인트
@router.post("/highlight")
async def create_highlighted_response(
        document_id: str,
        chunk_hash: str
):
    """
    특정 텍스트를 하이라이트한 PDF 생성 (캐시 활용)
    """
    try:
        # 1. 문서의 원본 청크 내용 조회
        chunk_query = vector_collection.get(where={"document_id": document_id, "chunk_hash": chunk_hash}, limit=1)
        if not chunk_query or not chunk_query["documents"]:
            raise HTTPException(status_code=404, detail="해당 청크를 찾을 수 없습니다.")
        search_text = chunk_query["documents"][0]

        # 2. 캐시된 PDF 파일 경로 가져오기
        try:
            pdf_file_path = get_document_pdf_path(document_id)
        except Exception as path_error:
            print(f"⚠️ 캐시된 PDF 파일 경로 조회 실패, 문서 정보로 fallback: {path_error}")
            doc_info = await get_document_info(document_id)
            if not doc_info.get('url'):
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
            pdf_file_path = ensure_pdf_cache_exists(document_id, doc_info)
            if not pdf_file_path:
                raise HTTPException(status_code=500, detail="PDF 파일을 준비할 수 없습니다.")

        # 3. 텍스트 위치 찾기
        locations = find_text_locations(pdf_file_path, search_text)

        if not locations:
            return {
                "status": "error",
                "message": "해당 텍스트를 찾을 수 없습니다."
            }

        # 하이라이트된 PDF 생성
        highlighted_path = create_highlighted_pdf(pdf_file_path, locations)

        # 하이라이트된 PDF를 Supabase Storage에 업로드
        highlighted_url = await upload_highlighted_pdf(highlighted_path, document_id)

        return {
            "status": "success",
            "highlighted_pdf_url": highlighted_url,
            "page_number": locations[0].page_number,
            "bbox": locations[0].bbox,
            "total_highlights": len(locations)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 하이라이트 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 하이라이트된 임시 파일만 정리 (원본 캐시는 유지)
        if 'highlighted_path' in locals() and os.path.exists(highlighted_path):
            os.remove(highlighted_path)


# 🔥 수정된 페이지 네비게이션 엔드포인트
@router.get("/page-navigation/{document_id}")
async def get_page_navigation_info(
        document_id: str,
        search_text: str = Query(..., description="검색할 텍스트")
):
    """
    특정 텍스트의 페이지 위치 정보 반환 (PDF 뷰어용, 캐시 활용)
    """
    try:
        # 캐시된 PDF 파일 경로 직접 활용
        try:
            pdf_file_path = get_document_pdf_path(document_id)
        except Exception as path_error:
            print(f"⚠️ 캐시된 PDF 파일 경로 조회 실패, 문서 정보로 fallback: {path_error}")
            # fallback: 문서 정보 조회 후 다운로드
            doc_info = await get_document_info(document_id)
            if not doc_info.get('url'):
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

            pdf_file_path = ensure_pdf_cache_exists(document_id, doc_info)
            if not pdf_file_path:
                raise HTTPException(status_code=500, detail="PDF 파일을 준비할 수 없습니다.")

        # 텍스트 위치 찾기
        locations = find_text_locations(pdf_file_path, search_text)

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

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 페이지 네비게이션 정보 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 🔥 문서 페이지 정보 조회 엔드포인트 추가
@router.get("/chat/{document_id}/pages")
async def get_document_pages(document_id: str):
    """
    문서의 총 페이지 수 조회
    """
    try:
        doc_info = await get_document_info(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        # 메타데이터에서 총 페이지 수 조회 또는 PDF에서 직접 계산
        total_pages = doc_info.get('total_pages', 1)

        return {
            "status": "success",
            "document_id": document_id,
            "total_pages": total_pages,
            "filename": doc_info.get('filename', 'Unknown')
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 문서 페이지 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def find_chunk_page_number(doc_info: Dict, chunk_text: str) -> int:
    """청크가 위치한 페이지 번호 찾기 (캐시된 PDF 파일 활용)"""
    try:
        document_id = doc_info.get('id')
        if not document_id:
            return 1

        # 캐시된 PDF 파일 경로 직접 활용
        try:
            pdf_file_path = get_document_pdf_path(document_id)
        except Exception as path_error:
            print(f"⚠️ 캐시된 PDF 파일 경로 조회 실패: {path_error}")
            # fallback: 원격 다운로드
            return await download_and_find_page_number(doc_info, chunk_text)

        # 캐시된 파일에서 텍스트 위치 찾기
        locations = find_text_locations(pdf_file_path, chunk_text[:100])
        if locations:
            return locations[0].page_number
        return 1

    except Exception as e:
        print(f"페이지 번호 찾기 실패: {e}")
        return 1


async def download_and_find_page_number(doc_info: Dict, chunk_text: str) -> int:
    """캐시 파일이 없을 때 원격에서 다운로드해서 페이지 번호 찾기 (fallback)"""
    try:
        if not doc_info.get('url'):
            return 1

        document_id = doc_info.get('id', 'unknown')

        # PDFFileManager를 통한 캐시 관리
        pdf_file_path = PDFFileManager.get_or_download(document_id, doc_info['url'])

        # 텍스트 위치 찾기
        locations = find_text_locations(pdf_file_path, chunk_text[:100])
        if locations:
            return locations[0].page_number
        return 1

    except Exception as e:
        print(f"원격 다운로드 후 페이지 번호 찾기 실패: {e}")
        return 1


def get_cached_pdf_path(document_id: str) -> str:
    """문서 ID로 캐시된 PDF 파일 경로 반환"""
    return PDFFileManager.get_cached_path(document_id)


def ensure_pdf_cache_exists(document_id: str, doc_info: Dict) -> str:
    """PDF 캐시 파일이 존재하는지 확인하고, 없으면 생성"""
    try:
        if PDFFileManager.is_cached(document_id):
            return PDFFileManager.get_cached_path(document_id)

        # 캐시 파일이 없으면 다운로드해서 생성
        if not doc_info.get('url'):
            return None

        cached_path = PDFFileManager.get_or_download(document_id, doc_info['url'])
        print(f"✅ PDF 캐시 파일 생성: {cached_path}")
        return cached_path

    except Exception as e:
        print(f"❌ PDF 캐시 파일 생성 실패: {e}")
        return None


async def upload_highlighted_pdf(file_path: str, document_id: str) -> str:
    """하이라이트된 PDF를 Supabase Storage에 업로드"""
    try:
        highlighted_filename = f"highlighted_{document_id}_{int(time.time())}.pdf"

        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Supabase Storage에 업로드
        upload_response = supabase.storage.from_("pdf-documents").upload(
            path=f"highlighted/{highlighted_filename}",
            file=file_content,
            file_options={"content-type": "application/pdf", "upsert": True}
        )

        # 공개 URL 생성
        public_url = supabase.storage.from_("pdf-documents").get_public_url(
            f"highlighted/{highlighted_filename}"
        ).data.get("publicUrl")

        return public_url

    except Exception as e:
        print(f"하이라이트된 PDF 업로드 실패: {e}")
        return ""


@router.post("/chat/search")
async def search_documents(query: str, document_ids: List[str] = None, limit: int = 10):
    """
    문서 검색 (답변 생성 없이 검색만, 페이지 정보 포함, 캐시 활용)
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
            document_id = metadata.get("document_id", "")
            start_page = metadata.get("start_page", 1)
            end_page = metadata.get("end_page", 1)

            results.append({
                "document_id": document_id,
                "filename": metadata.get("filename", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "content": doc,
                "relevance_score": 1 - distance,
                "distance": distance,
                "page_number": start_page,
                "end_page": end_page,
                "chunk_hash": metadata.get("chunk_hash", ""),
                "char_count": metadata.get("char_count", len(doc)),
                "created_at": metadata.get("created_at", ""),
                "navigation_info": {
                    "can_highlight": True,
                    "can_navigate": True,
                    "is_cached": PDFFileManager.is_cached(document_id)
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
    채팅에 사용 가능한 문서 목록 조회 (완료된 문서만, 캐시 상태 포함)
    """
    try:
        response = supabase.from_('documents').select('id, filename, created_at, processed_at').eq('status',
                                                                                                   'completed').order(
            'created_at', desc=True).execute()

        # 캐시 상태 정보 추가
        documents_with_cache_info = []
        for doc in response.data:
            doc_with_cache = doc.copy()
            doc_with_cache['is_cached'] = PDFFileManager.is_cached(doc['id'])
            documents_with_cache_info.append(doc_with_cache)

        return {
            "status": "success",
            "documents": documents_with_cache_info,
            "count": len(documents_with_cache_info)
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


@router.get("/chat/cache-status")
async def get_cache_status():
    """
    PDF 캐시 상태 조회 (디버깅 및 모니터링용)
    """
    try:
        cache_info = []

        # 완료된 모든 문서 조회
        response = supabase.from_('documents').select('id, filename, status').eq('status', 'completed').execute()

        for doc in response.data:
            document_id = doc['id']
            is_cached = PDFFileManager.is_cached(document_id)
            cache_path = PDFFileManager.get_cached_path(document_id)

            file_size = 0
            if is_cached and os.path.exists(cache_path):
                file_size = os.path.getsize(cache_path)

            cache_info.append({
                "document_id": document_id,
                "filename": doc['filename'],
                "is_cached": is_cached,
                "cache_path": cache_path if is_cached else None,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2) if file_size > 0 else 0
            })

        total_cached = sum(1 for info in cache_info if info['is_cached'])
        total_size_mb = sum(info['file_size_mb'] for info in cache_info)

        return {
            "status": "success",
            "summary": {
                "total_documents": len(cache_info),
                "total_cached": total_cached,
                "cache_hit_rate": round(total_cached / len(cache_info) * 100, 1) if cache_info else 0,
                "total_cache_size_mb": round(total_size_mb, 2)
            },
            "cache_details": cache_info
        }

    except Exception as e:
        print(f"❌ 캐시 상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear-cache")
async def clear_document_cache(document_id: str = None):
    """
    PDF 캐시 정리 (특정 문서 또는 전체)
    """
    try:
        if document_id:
            # 특정 문서 캐시 삭제
            if PDFFileManager.is_cached(document_id):
                PDFFileManager.cleanup_cache(document_id)
                return {
                    "status": "success",
                    "message": f"문서 {document_id}의 캐시가 삭제되었습니다."
                }
            else:
                return {
                    "status": "success",
                    "message": f"문서 {document_id}의 캐시가 존재하지 않습니다."
                }
        else:
            # 전체 캐시 정리는 보안상 제한적으로 구현
            return {
                "status": "error",
                "message": "전체 캐시 삭제는 시스템 관리자만 수행할 수 있습니다."
            }

    except Exception as e:
        print(f"❌ 캐시 정리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))