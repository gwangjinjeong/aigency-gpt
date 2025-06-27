# backend/app/api/chat.py
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.document_processor import vector_collection
from app.services.vectorizer import get_embeddings
from app.services.supabase_client import supabase
import openai
import time
from typing import List, Dict, Any
import traceback

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """
    문서 기반 질의응답
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

                sources.append({
                    "document_id": metadata.get("document_id", ""),
                    "filename": metadata.get("filename", "Unknown"),
                    "chunk_index": metadata.get("chunk_index", i),
                    "relevance_score": 1 - distance,  # 거리를 유사도로 변환
                    "content_preview": doc[:200] + "..." if len(doc) > 200 else doc
                })

        if not context_chunks:
            return ChatResponse(
                status="success",
                answer="질문과 관련된 정보의 유사도가 낮아 정확한 답변을 제공하기 어렵습니다.",
                sources=[],
                document_ids=[],
                processing_time=time.time() - start_time
            )

        # 4. OpenAI API로 답변 생성
        context = "\n\n".join(context_chunks[:3])  # 상위 3개 청크만 사용

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


@router.post("/chat/search")
async def search_documents(query: str, document_ids: List[str] = None, limit: int = 10):
    """
    문서 검색 (답변 생성 없이 검색만)
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

        # 결과 정리
        documents = search_results["documents"][0]
        metadatas = search_results["metadatas"][0]
        distances = search_results["distances"][0]

        results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            results.append({
                "document_id": metadata.get("document_id", ""),
                "filename": metadata.get("filename", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "content": doc,
                "relevance_score": 1 - distance,
                "distance": distance
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
        feedback_text: str = None
):
    """
    채팅 답변에 대한 피드백 수집
    """
    try:
        # 피드백을 로그나 별도 테이블에 저장할 수 있음
        feedback_data = {
            "message": message,
            "answer": answer,
            "rating": rating,
            "feedback_text": feedback_text,
            "timestamp": time.time()
        }

        # 여기서는 단순히 로그만 출력
        print(f"📝 사용자 피드백: {feedback_data}")

        return {
            "status": "success",
            "message": "피드백이 저장되었습니다."
        }

    except Exception as e:
        print(f"❌ 피드백 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))