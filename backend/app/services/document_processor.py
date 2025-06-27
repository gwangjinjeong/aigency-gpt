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
import tempfile
import shutil
from pathlib import Path

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection_name = "pdf_document_embeddings"

try:
    vector_collection = chroma_client.get_collection(name=collection_name)
    print(f"ChromaDB collection '{collection_name}'이 이미 존재합니다.")
except Exception:
    vector_collection = chroma_client.create_collection(name=collection_name)
    print(f"ChromaDB collection '{collection_name}'을 새로 생성했습니다.")

# 🔥 PDF 파일 캐시 관리
PDF_CACHE_DIR = "./pdf_cache"
os.makedirs(PDF_CACHE_DIR, exist_ok=True)


class PDFFileManager:
    """PDF 파일 생명주기 관리 클래스"""

    @staticmethod
    def get_cached_path(document_id: str) -> str:
        """캐시된 PDF 파일 경로 반환"""
        return os.path.join(PDF_CACHE_DIR, f"{document_id}.pdf")

    @staticmethod
    def is_cached(document_id: str) -> bool:
        """PDF 파일이 캐시되어 있는지 확인"""
        cached_path = PDFFileManager.get_cached_path(document_id)
        return os.path.exists(cached_path) and os.path.getsize(cached_path) > 0

    @staticmethod
    def save_to_cache(document_id: str, file_content: bytes) -> str:
        """PDF 파일을 캐시에 저장"""
        cached_path = PDFFileManager.get_cached_path(document_id)
        with open(cached_path, 'wb') as f:
            f.write(file_content)
        return cached_path

    @staticmethod
    def get_or_download(document_id: str, file_url: str) -> str:
        """캐시에서 파일을 가져오거나 새로 다운로드"""
        cached_path = PDFFileManager.get_cached_path(document_id)

        # 캐시에 있으면 반환
        if PDFFileManager.is_cached(document_id):
            print(f"[{document_id}] 캐시된 파일 사용: {cached_path}")
            return cached_path

        # 없으면 다운로드 후 캐시에 저장
        print(f"[{document_id}] 파일 다운로드 및 캐시 저장...")
        file_content = PDFFileManager._download_file(file_url, document_id)
        return PDFFileManager.save_to_cache(document_id, file_content)

    @staticmethod
    def _download_file(file_url: str, document_id: str) -> bytes:
        """파일 다운로드 (Supabase Storage 또는 공개 URL)"""
        bucket_name = "pdf-documents"

        try:
            # Supabase Storage에서 다운로드 시도
            if f"/{bucket_name}/" in file_url:
                path_in_storage = file_url.split(f"/{bucket_name}/")[-1]
            else:
                path_in_storage = file_url.split("/")[-1]

            print(f"[{document_id}] Supabase Storage에서 다운로드: {path_in_storage}")
            file_bytes = supabase.storage.from_(bucket_name).download(path_in_storage)

            if file_bytes and isinstance(file_bytes, bytes) and len(file_bytes) > 0:
                print(f"[{document_id}] Supabase Storage 다운로드 성공: {len(file_bytes)} bytes")
                return file_bytes
            else:
                raise Exception("Supabase Storage에서 빈 파일 또는 잘못된 응답")

        except Exception as storage_error:
            print(f"[{document_id}] Supabase Storage 다운로드 실패: {storage_error}")

            # 공개 URL로 대안 다운로드
            try:
                print(f"[{document_id}] 공개 URL로 다운로드 시도...")
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()

                if len(response.content) == 0:
                    raise Exception("공개 URL에서 빈 파일 다운로드됨")

                print(f"[{document_id}] 공개 URL 다운로드 성공: {len(response.content)} bytes")
                return response.content

            except Exception as url_error:
                raise Exception(f"모든 다운로드 방법 실패 - Storage: {storage_error}, URL: {url_error}")

    @staticmethod
    def cleanup_cache(document_id: str = None):
        """캐시 파일 정리"""
        if document_id:
            # 특정 문서 캐시 삭제
            cached_path = PDFFileManager.get_cached_path(document_id)
            if os.path.exists(cached_path):
                os.remove(cached_path)
                print(f"[{document_id}] 캐시 파일 삭제: {cached_path}")
        else:
            # 전체 캐시 정리 (선택적)
            pass


async def download_pdf_from_supabase(file_url: str, document_id: str) -> str:
    """
    🔥 개선된 PDF 다운로드 (캐시 활용)
    """
    return PDFFileManager.get_or_download(document_id, file_url)


async def process_single_document(document_id: str, filename: str, file_url: str) -> Dict:
    """
    🔥 개선된 단일 PDF 문서 처리 (파일 생명주기 관리 개선)
    """
    pdf_file_path = None

    try:
        print(f"[{document_id}] 문서 처리 시작: {filename}")

        # 1. PDF 파일 획득 (캐시 우선 활용)
        print(f"[{document_id}] PDF 파일 획득 시작: {file_url}")
        pdf_file_path = await download_pdf_from_supabase(file_url, document_id)

        # 2. 파일 유효성 검증
        if not os.path.exists(pdf_file_path):
            raise Exception(f"PDF 파일을 찾을 수 없습니다: {pdf_file_path}")

        file_size = os.path.getsize(pdf_file_path)
        if file_size == 0:
            raise Exception("PDF 파일이 비어있습니다")

        print(f"[{document_id}] PDF 파일 확인됨: {pdf_file_path} ({file_size} bytes)")

        # 3. PDF 위치 정보 포함 벡터화 처리
        print(f"[{document_id}] PDF 위치 정보 포함 벡터화 처리 시작...")
        vectorization_result = process_pdf_file_with_locations(pdf_file_path)

        if vectorization_result["status"] != "success":
            raise Exception(f"PDF 벡터화 처리 실패: {vectorization_result.get('error', 'Unknown error')}")

        chunks = vectorization_result["chunks"]
        chunks_with_locations = vectorization_result["chunks_with_locations"]

        if not chunks:
            raise Exception("PDF에서 유효한 텍스트 청크를 생성할 수 없습니다")

        # 4. 임베딩 생성
        print(f"[{document_id}] 임베딩 생성 중...")
        embeddings = get_embeddings(chunks)

        if len(chunks) != len(embeddings):
            raise Exception(f"청크 수({len(chunks)})와 임베딩 수({len(embeddings)})가 일치하지 않습니다")

        # 5. ChromaDB에 청크와 임베딩 저장 (위치 정보 포함)
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
                "created_at": datetime.now().isoformat(),
                "pdf_file_path": pdf_file_path  # 🔥 파일 경로 저장
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

        # 6. Supabase DB의 문서 상태를 'completed'로 업데이트
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
            "pdf_file_path": pdf_file_path,  # 🔥 파일 경로 반환 (하이라이트용)
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

    # 🔥 임시 파일 삭제하지 않음 - 캐시로 유지하여 후속 작업에서 활용


def get_document_pdf_path(document_id: str) -> str:
    """
    🔥 문서 ID로 PDF 파일 경로 조회 (캐시 우선)
    """
    # 1. 캐시에서 확인
    if PDFFileManager.is_cached(document_id):
        return PDFFileManager.get_cached_path(document_id)

    # 2. ChromaDB 메타데이터에서 확인
    try:
        results = vector_collection.get(
            where={"document_id": document_id},
            limit=1
        )

        if results["metadatas"] and results["metadatas"][0]:
            stored_path = results["metadatas"][0].get("pdf_file_path")
            if stored_path and os.path.exists(stored_path):
                return stored_path
    except Exception as e:
        print(f"ChromaDB에서 파일 경로 조회 실패: {e}")

    # 3. Supabase에서 URL 조회 후 다운로드
    try:
        response = supabase.from_('documents').select('url').eq('id', document_id).execute()
        if response.data:
            file_url = response.data[0]['url']
            return PDFFileManager.get_or_download(document_id, file_url)
    except Exception as e:
        print(f"Supabase에서 파일 URL 조회 실패: {e}")

    raise Exception(f"문서 {document_id}의 PDF 파일을 찾을 수 없습니다")


def find_chunk_exact_location(document_id: str, chunk_text: str, file_url: str = None) -> Dict:
    """
    🔥 개선된 청크 위치 찾기 (캐시된 파일 활용)
    """
    try:
        # PDF 파일 경로 획득
        pdf_file_path = get_document_pdf_path(document_id)

        # 텍스트 위치 찾기
        search_text = chunk_text[:200]  # 청크의 첫 200자로 검색
        locations = find_text_locations(pdf_file_path, search_text)

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
                "total_matches": len(locations),
                "pdf_file_path": pdf_file_path
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


def search_similar_documents_with_pages(query_text: str, limit: int = 5, document_ids: List[str] = None) -> Dict:
    """
    🔥 개선된 문서 검색 (PDF 파일 경로 포함)
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
            # 🔥 PDF 파일 경로 확인
            try:
                pdf_path = get_document_pdf_path(metadata.get("document_id", ""))
            except:
                pdf_path = None

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
                "created_at": metadata.get("created_at", ""),
                "pdf_file_path": pdf_path  # 🔥 PDF 파일 경로 추가
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


# 🔥 나머지 함수들은 기존과 동일하게 유지...
def get_document_status(document_id: str) -> Dict:
    """특정 문서의 처리 상태를 조회합니다."""
    try:
        response = supabase.from_('documents').select('*').eq('id', document_id).execute()
        if response.data:
            return {"status": "success", "data": response.data[0]}
        else:
            return {"status": "not_found", "message": "문서를 찾을 수 없습니다"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_documents_by_status(status: str = None, limit: int = 10) -> Dict:
    """상태별로 문서 목록을 조회합니다."""
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


def delete_document_vectors(document_id: str) -> Dict:
    """
    🔥 개선된 문서 벡터 삭제 (캐시도 함께 정리)
    """
    try:
        # ChromaDB에서 벡터 데이터 삭제
        results = vector_collection.get(where={"document_id": document_id})

        if not results["ids"]:
            return {
                "status": "not_found",
                "message": "삭제할 벡터 데이터가 없습니다."
            }

        vector_collection.delete(ids=results["ids"])

        # 캐시 파일도 삭제
        PDFFileManager.cleanup_cache(document_id)

        return {
            "status": "success",
            "message": f"{len(results['ids'])}개의 벡터 데이터가 삭제되었습니다.",
            "deleted_count": len(results["ids"])
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# 하위 호환성을 위한 기존 함수들
def search_similar_documents(query_text: str, limit: int = 5) -> Dict:
    """기존 검색 함수 (하위 호환성)"""
    return search_similar_documents_with_pages(query_text, limit)


def get_document_page_info(document_id: str) -> Dict:
    """문서의 페이지 정보를 조회합니다."""
    try:
        results = vector_collection.get(where={"document_id": document_id})

        if not results["ids"]:
            return {"status": "not_found", "message": "문서를 찾을 수 없습니다."}

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
        return {"status": "error", "message": str(e)}


async def reprocess_failed_documents() -> Dict:
    """실패한 문서들을 재처리합니다."""
    try:
        response = supabase.from_('documents').select('*').eq('status', 'failed').execute()
        failed_docs = response.data

        if not failed_docs:
            return {"status": "success", "message": "재처리할 실패 문서가 없습니다", "count": 0}

        success_count = 0
        results = []

        for doc in failed_docs:
            print(f"재처리 시작: {doc['filename']} (ID: {doc['id']})")

            supabase.from_('documents').update({
                'status': 'pending',
                'processed_at': None
            }).eq('id', doc['id']).execute()

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
    """청크 해시로 특정 청크 정보를 조회합니다."""
    try:
        results = vector_collection.get(where={"chunk_hash": chunk_hash})

        if not results["ids"]:
            return {"status": "not_found", "message": "해당 청크를 찾을 수 없습니다."}

        chunk_data = {
            "chunk_id": results["ids"][0],
            "document": results["documents"][0],
            "metadata": results["metadatas"][0]
        }

        return {"status": "success", "chunk": chunk_data}

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    print("✨ Enhanced Document processor 모듈이 준비되었습니다.")
    print("🔥 개선사항:")
    print("  - PDF 파일 캐시 관리")
    print("  - 파일 생명주기 최적화")
    print("  - 경로 불일치 문제 해결")
    print("  - 페이지 위치 정보 및 하이라이트 기능 지원")