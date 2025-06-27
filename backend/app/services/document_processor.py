# backend/app/services/document_processor.py (Enhanced for RAG with Location)
import requests
import os
import chromadb
from app.services.supabase_client import supabase
from app.services.pdf_service import process_pdf_file_with_locations, find_text_locations
from app.services.vectorizer import get_embeddings
from datetime import datetime
from typing import List, Dict
import traceback
import json

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection_name = "pdf_document_embeddings"

try:
    vector_collection = chroma_client.get_collection(name=collection_name)
    print(f"ChromaDB collection '{collection_name}'이 이미 존재합니다.")
except Exception:
    vector_collection = chroma_client.create_collection(name=collection_name)
    print(f"ChromaDB collection '{collection_name}'을 새로 생성했습니다.")


async def download_pdf_from_supabase(file_url: str, document_id: str) -> str:
    """
    Supabase Storage의 PDF 파일을 다운로드하여 로컬에 저장합니다.
    """
    bucket_name = "pdf-documents"

    try:
        if f"/{bucket_name}/" in file_url:
            path_in_storage = file_url.split(f"/{bucket_name}/")[-1]
        else:
            path_in_storage = file_url.split("/")[-1]

        print(f"[{document_id}] Storage 경로: {path_in_storage}")
    except Exception as e:
        raise Exception(f"파일 경로 추출 실패: {e}")

    # 임시 파일 경로 설정
    temp_file_path = f"/tmp/{document_id}.pdf"
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    try:
        print(f"[{document_id}] Supabase Storage에서 다운로드 시작...")

        # Supabase에서 파일 다운로드
        file_bytes = supabase.storage.from_(bucket_name).download(path_in_storage)

        if file_bytes is None:
            raise Exception("파일 다운로드 실패: 빈 응답")

        if not isinstance(file_bytes, bytes):
            raise Exception(f"예상치 못한 응답 타입: {type(file_bytes)}")

        # 파일 저장
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        file_size = os.path.getsize(temp_file_path)
        if file_size == 0:
            raise Exception("다운로드된 파일이 비어있습니다")

        print(f"[{document_id}] PDF 파일 다운로드 성공: {temp_file_path} ({file_size} bytes)")
        return temp_file_path

    except Exception as e:
        print(f"[{document_id}] Supabase Storage 다운로드 중 오류 발생: {e}")

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # 대안: 공개 URL로 직접 다운로드 시도
        try:
            print(f"[{document_id}] 공개 URL로 직접 다운로드 시도...")
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()

            with open(temp_file_path, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(temp_file_path)
            if file_size == 0:
                raise Exception("공개 URL에서 다운로드된 파일이 비어있습니다")

            print(f"[{document_id}] 공개 URL로 다운로드 성공: {temp_file_path} ({file_size} bytes)")
            return temp_file_path

        except Exception as fallback_error:
            print(f"[{document_id}] 공개 URL 다운로드도 실패: {fallback_error}")
            raise Exception(f"파일 다운로드 실패 - Storage API: {e}, 공개 URL: {fallback_error}")


async def process_single_document(document_id: str, filename: str, file_url: str) -> Dict:
    """
    단일 PDF 문서를 다운로드, 청크 분할, 임베딩, ChromaDB 저장까지 처리합니다.
    위치 정보를 포함하여 처리합니다.
    """
    temp_pdf_path = None

    try:
        print(f"[{document_id}] 문서 처리 시작: {filename}")

        # 1. Supabase Storage에서 PDF 다운로드
        print(f"[{document_id}] 파일 다운로드 시작: {file_url}")
        temp_pdf_path = await download_pdf_from_supabase(file_url, document_id)

        # 2. PDF 위치 정보 포함 벡터화 처리
        print(f"[{document_id}] PDF 위치 정보 포함 벡터화 처리 시작...")
        vectorization_result = process_pdf_file_with_locations(temp_pdf_path)

        if vectorization_result["status"] != "success":
            raise Exception(f"PDF 벡터화 처리 실패: {vectorization_result.get('error', 'Unknown error')}")

        chunks = vectorization_result["chunks"]
        chunks_with_locations = vectorization_result["chunks_with_locations"]

        if not chunks:
            raise Exception("PDF에서 유효한 텍스트 청크를 생성할 수 없습니다")

        # 3. 임베딩 생성
        print(f"[{document_id}] 임베딩 생성 중...")
        embeddings = get_embeddings(chunks)

        if len(chunks) != len(embeddings):
            raise Exception(f"청크 수({len(chunks)})와 임베딩 수({len(embeddings)})가 일치하지 않습니다")

        # 4. ChromaDB에 청크와 임베딩 저장 (위치 정보 포함)
        print(f"[{document_id}] ChromaDB에 {len(chunks)}개 임베딩 저장 중...")

        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []

        for i, chunk_location in enumerate(chunks_with_locations):
            metadata = {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "start_page": chunk_location["start_page"],
                "end_page": chunk_location["end_page"],
                "chunk_hash": chunk_location["chunk_hash"],
                "char_count": chunk_location["char_count"],
                "created_at": datetime.now().isoformat()
            }
            metadatas.append(metadata)

        # ChromaDB에 저장 (기존 ID가 있다면 삭제 후 추가)
        try:
            # 기존 데이터 확인 및 삭제
            existing_ids = []
            try:
                existing_data = vector_collection.get(
                    where={"document_id": document_id}
                )
                if existing_data["ids"]:
                    existing_ids = existing_data["ids"]
                    print(f"[{document_id}] 기존 {len(existing_ids)}개 청크 발견, 삭제 후 재추가")
                    vector_collection.delete(ids=existing_ids)
            except Exception as get_error:
                print(f"[{document_id}] 기존 데이터 확인 중 오류 (무시): {get_error}")

            # 새 데이터 추가
            vector_collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[{document_id}] {len(chunks)}개의 청크가 ChromaDB에 성공적으로 저장되었습니다.")

        except Exception as chroma_error:
            raise Exception(f"ChromaDB 저장 실패: {chroma_error}")

        # 5. Supabase DB의 문서 상태를 'completed'로 업데이트
        print(f"[{document_id}] Supabase DB 상태 'completed'로 업데이트 중...")

        try:
            update_response = supabase.from_('documents').update({
                'status': 'completed',
                'processed_at': datetime.now().isoformat(),
            }).eq('id', document_id).execute()

            print(f"[{document_id}] DB 상태 업데이트 성공")

        except Exception as db_error:
            raise Exception(f"Supabase DB 상태 업데이트 실패: {db_error}")

        print(f"[{document_id}] ✅ 모든 처리 완료. 상태: completed")
        return {
            "status": "success",
            "message": f"문서 '{filename}' 처리 완료. {len(chunks)}개 청크 저장됨.",
            "chunk_count": len(chunks),
            "document_id": document_id,
            "location_info": {
                "total_pages": vectorization_result.get("text_extraction", {}).get("total_pages", 0),
                "chunks_with_pages": chunks_with_locations
            }
        }

    except Exception as e:
        error_msg = str(e)
        print(f"[{document_id}] ❌ 문서 처리 중 오류 발생: {error_msg}")
        traceback.print_exc()

        # 오류 발생 시 Supabase DB 상태를 'failed'로 업데이트
        try:
            print(f"[{document_id}] DB 상태를 'failed'로 업데이트 중...")
            update_response = supabase.from_('documents').update({
                'status': 'failed',
                'processed_at': datetime.now().isoformat(),
            }).eq('id', document_id).execute()

            print(f"[{document_id}] 실패 상태 업데이트 완료")

        except Exception as db_update_err:
            print(f"[{document_id}] ⚠️ 실패 상태 업데이트 중 오류 발생: {db_update_err}")

        return {
            "status": "failed",
            "message": f"문서 '{filename}' 처리 실패: {error_msg}",
            "document_id": document_id
        }

    finally:
        # 임시 다운로드 파일 삭제
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"[{document_id}] 임시 파일 삭제 완료: {temp_pdf_path}")
            except Exception as cleanup_error:
                print(f"[{document_id}] ⚠️ 임시 파일 삭제 실패: {cleanup_error}")


def get_document_status(document_id: str) -> Dict:
    """
    특정 문서의 처리 상태를 조회합니다.
    """
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()

        if response.data:
            return {"status": "success", "data": response.data[0]}
        else:
            return {"status": "not_found", "message": "문서를 찾을 수 없습니다"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_documents_by_status(status: str = None, limit: int = 10) -> Dict:
    """
    상태별로 문서 목록을 조회합니다.
    """
    try:
        query = supabase.from_('documents').select('*').order('created_at', desc=True).limit(limit)

        if status:
            query = query.eq('status', status)

        response = query.execute()

        return {
            "status": "success",
            "data": response.data,
            "count": len(response.data)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_similar_documents_with_pages(query_text: str, limit: int = 5, document_ids: List[str] = None) -> Dict:
    """
    ChromaDB에서 유사한 문서 청크를 검색합니다. (페이지 정보 포함)
    """
    try:
        # 쿼리 텍스트를 임베딩으로 변환
        query_embedding = get_embeddings([query_text])[0]

        # 검색 조건 설정
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": limit
        }

        # 특정 문서에서만 검색하는 경우
        if document_ids:
            search_kwargs["where"] = {
                "document_id": {"$in": document_ids}
            }

        # ChromaDB에서 검색
        results = vector_collection.query(**search_kwargs)

        if not results["documents"] or not results["documents"][0]:
            return {
                "status": "success",
                "results": [],
                "message": "검색 결과가 없습니다."
            }

        # 결과 정리 (페이지 정보 포함)
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        search_results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            result = {
                "document_id": metadata.get("document_id", ""),
                "filename": metadata.get("filename", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "content": doc,
                "relevance_score": 1 - distance,
                "distance": distance,
                "page_number": metadata.get("start_page", 1),
                "end_page": metadata.get("end_page", 1),
                "chunk_hash": metadata.get("chunk_hash", ""),
                "char_count": metadata.get("char_count", len(doc)),
                "created_at": metadata.get("created_at", "")
            }
            search_results.append(result)

        return {
            "status": "success",
            "results": search_results,
            "query": query_text,
            "total_results": len(search_results)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def find_chunk_exact_location(document_id: str, chunk_text: str, file_url: str) -> Dict:
    """
    특정 청크의 정확한 PDF 위치를 찾습니다.
    """
    temp_file_path = None
    try:
        # PDF 다운로드
        import requests
        response = requests.get(file_url)
        response.raise_for_status()

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            temp_file_path = tmp_file.name

        # 텍스트 위치 찾기
        search_text = chunk_text[:200]  # 청크의 첫 200자로 검색
        locations = find_text_locations(temp_file_path, search_text)

        if locations:
            primary_location = locations[0]
            return {
                "status": "success",
                "page_number": primary_location.page_number,
                "bbox": {
                    "x0": primary_location.bbox[0],
                    "y0": primary_location.bbox[1],
                    "x1": primary_location.bbox[2],
                    "y1": primary_location.bbox[3]
                },
                "context": primary_location.context,
                "total_matches": len(locations)
            }
        else:
            return {
                "status": "not_found",
                "message": "해당 텍스트를 PDF에서 찾을 수 없습니다."
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        # 임시 파일 정리
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def get_document_page_info(document_id: str) -> Dict:
    """
    문서의 페이지 정보를 조회합니다.
    """
    try:
        # ChromaDB에서 해당 문서의 모든 청크 조회
        results = vector_collection.get(
            where={"document_id": document_id}
        )

        if not results["ids"]:
            return {
                "status": "not_found",
                "message": "문서를 찾을 수 없습니다."
            }

        # 페이지 정보 수집
        page_info = {}
        total_chunks = len(results["ids"])

        for metadata in results["metadatas"]:
            start_page = metadata.get("start_page", 1)
            end_page = metadata.get("end_page", 1)

            for page in range(start_page, end_page + 1):
                if page not in page_info:
                    page_info[page] = {
                        "page_number": page,
                        "chunk_count": 0,
                        "chunks": []
                    }

                page_info[page]["chunk_count"] += 1
                page_info[page]["chunks"].append({
                    "chunk_index": metadata.get("chunk_index", 0),
                    "chunk_hash": metadata.get("chunk_hash", ""),
                    "char_count": metadata.get("char_count", 0)
                })

        return {
            "status": "success",
            "document_id": document_id,
            "total_chunks": total_chunks,
            "total_pages": len(page_info),
            "page_info": list(page_info.values())
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


async def reprocess_failed_documents() -> Dict:
    """
    실패한 문서들을 재처리합니다.
    """
    try:
        # 실패한 문서 조회
        response = supabase.from_('documents').select('*').eq('status', 'failed').execute()
        failed_docs = response.data

        if not failed_docs:
            return {"status": "success", "message": "재처리할 실패 문서가 없습니다", "count": 0}

        success_count = 0
        results = []

        for doc in failed_docs:
            print(f"재처리 시작: {doc['filename']} (ID: {doc['id']})")

            # 상태를 pending으로 변경
            supabase.from_('documents').update({
                'status': 'pending',
                'processed_at': None
            }).eq('id', doc['id']).execute()

            # 재처리
            result = await process_single_document(doc['id'], doc['filename'], doc['url'])
            results.append({
                "document_id": doc['id'],
                "filename": doc['filename'],
                "result": result
            })

            if result['status'] == 'success':
                success_count += 1

        return {
            "status": "success",
            "message": f"{len(failed_docs)}개 문서 재처리 완료. 성공: {success_count}개",
            "total_processed": len(failed_docs),
            "success_count": success_count,
            "results": results
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_chunk_by_hash(chunk_hash: str) -> Dict:
    """
    청크 해시로 특정 청크 정보를 조회합니다.
    """
    try:
        results = vector_collection.get(
            where={"chunk_hash": chunk_hash}
        )

        if not results["ids"]:
            return {
                "status": "not_found",
                "message": "해당 청크를 찾을 수 없습니다."
            }

        # 첫 번째 결과 반환
        chunk_data = {
            "chunk_id": results["ids"][0],
            "document": results["documents"][0],
            "metadata": results["metadatas"][0]
        }

        return {
            "status": "success",
            "chunk": chunk_data
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def delete_document_vectors(document_id: str) -> Dict:
    """
    특정 문서의 모든 벡터 데이터를 삭제합니다.
    """
    try:
        # 해당 문서의 모든 벡터 데이터 조회
        results = vector_collection.get(
            where={"document_id": document_id}
        )

        if not results["ids"]:
            return {
                "status": "not_found",
                "message": "삭제할 벡터 데이터가 없습니다."
            }

        # 벡터 데이터 삭제
        vector_collection.delete(ids=results["ids"])

        return {
            "status": "success",
            "message": f"{len(results['ids'])}개의 벡터 데이터가 삭제되었습니다.",
            "deleted_count": len(results["ids"])
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# 기존 함수도 유지 (하위 호환성)
def search_similar_documents(query_text: str, limit: int = 5) -> Dict:
    """
    ChromaDB에서 유사한 문서 청크를 검색합니다. (기존 버전)
    """
    return search_similar_documents_with_pages(query_text, limit)


if __name__ == "__main__":
    # 테스트용 코드
    import asyncio


    async def test_processing():
        # 예시: pending 상태 문서 처리 테스트
        try:
            response = supabase.from_('documents').select('*').eq('status', 'pending').limit(1).execute()
            if response.data:
                doc = response.data[0]
                result = await process_single_document(doc['id'], doc['filename'], doc['url'])
                print(f"테스트 결과: {result}")
            else:
                print("테스트할 pending 상태 문서가 없습니다.")

            # 검색 테스트
            search_result = search_similar_documents_with_pages("대출 조건", limit=3)
            print(f"검색 테스트 결과: {search_result}")

        except Exception as e:
            print(f"테스트 중 오류: {e}")


    # asyncio.run(test_processing())
    print("Enhanced Document processor 모듈이 준비되었습니다.")
    print("✨ 페이지 위치 정보 및 하이라이트 기능 지원")