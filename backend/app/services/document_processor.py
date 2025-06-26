#llm_doc_poc/document_processor.py
import requests
import os
import chromadb
from supabase_client import supabase
from vectorizer import process_pdf_for_vectorization
from datetime import datetime
from typing import List, Dict
import traceback
from postgrest.exceptions import APIError

# ChromaDB 클라이언트 초기화 (로컬에서 실행)
# PersistentClient를 사용하여 데이터가 디스크에 저장되도록 합니다.
# PoC 단계에서는 간단히 인메모리 또는 로컬 파일 시스템 사용
# collection_name은 필요에 따라 변경 가능
chroma_client = chromadb.PersistentClient(path="./chroma_db")  # ./chroma_db 폴더에 저장
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
    Supabase 2.16.0 호환 버전
    """
    bucket_name = "pdf-documents"

    # URL에서 파일 경로 추출
    # 예: "https://[project_id].supabase.co/storage/v1/object/public/pdf-documents/unique_filename.pdf"
    # 에서 "unique_filename.pdf" 부분만 필요
    try:
        if f"/{bucket_name}/" in file_url:
            path_in_storage = file_url.split(f"/{bucket_name}/")[-1]
        else:
            # URL 구조가 다를 경우 대안 방법
            path_in_storage = file_url.split("/")[-1]

        print(f"[{document_id}] Storage 경로: {path_in_storage}")
    except Exception as e:
        raise Exception(f"파일 경로 추출 실패: {e}")

    # 임시 파일 경로 설정
    temp_file_path = f"/tmp/{document_id}.pdf"
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    try:
        print(f"[{document_id}] Supabase Storage에서 다운로드 시작...")

        # Supabase 2.16.0에서는 download() 메서드가 직접 bytes를 반환
        file_bytes = supabase.storage.from_(bucket_name).download(path_in_storage)

        # file_bytes가 None이 아니고 bytes 타입인지 확인
        if file_bytes is None:
            raise Exception("파일 다운로드 실패: 빈 응답")

        if not isinstance(file_bytes, bytes):
            raise Exception(f"예상치 못한 응답 타입: {type(file_bytes)}")

        # 파일 저장
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        # 파일 크기 확인
        file_size = os.path.getsize(temp_file_path)
        if file_size == 0:
            raise Exception("다운로드된 파일이 비어있습니다")

        print(f"[{document_id}] PDF 파일 다운로드 성공: {temp_file_path} ({file_size} bytes)")
        return temp_file_path

    except Exception as e:
        print(f"[{document_id}] Supabase Storage 다운로드 중 오류 발생: {e}")

        # 파일이 생성되었지만 오류가 발생한 경우 정리
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
    Supabase 2.16.0 호환 버전
    """
    temp_pdf_path = None

    try:
        print(f"[{document_id}] 문서 처리 시작: {filename}")

        # 1. Supabase Storage에서 PDF 다운로드
        print(f"[{document_id}] 파일 다운로드 시작: {file_url}")
        temp_pdf_path = await download_pdf_from_supabase(file_url, document_id)

        # 2. PDF 청크 분할 및 임베딩 생성
        print(f"[{document_id}] PDF 벡터화 처리 시작...")
        vectorization_result = process_pdf_for_vectorization(temp_pdf_path)

        if vectorization_result["status"] != "success":
            raise Exception(f"PDF 벡터화 처리 실패: {vectorization_result['message']}")

        chunks = vectorization_result["chunks"]
        embeddings = vectorization_result["embeddings"]

        if not chunks or not embeddings:
            raise Exception("PDF에서 유효한 텍스트 청크나 임베딩을 생성할 수 없습니다")

        if len(chunks) != len(embeddings):
            raise Exception(f"청크 수({len(chunks)})와 임베딩 수({len(embeddings)})가 일치하지 않습니다")

        # 3. ChromaDB에 청크와 임베딩 저장
        print(f"[{document_id}] ChromaDB에 {len(chunks)}개 임베딩 저장 중...")

        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "created_at": datetime.now().isoformat()
            }
            for i in range(len(chunks))
        ]

        # ChromaDB에 저장 (기존 ID가 있다면 삭제 후 추가)
        try:
            # 기존 데이터 확인 및 삭제
            existing_ids = []
            try:
                existing_data = vector_collection.get(ids=ids)
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

        # 4. Supabase DB의 문서 상태를 'completed'로 업데이트
        print(f"[{document_id}] Supabase DB 상태 'completed'로 업데이트 중...")

        try:
            update_response = supabase.from_('documents').update({
                'status': 'completed',
                'processed_at': datetime.now().isoformat(),
            }).eq('id', document_id).execute()

            # Supabase 2.16.0에서는 예외가 발생하지 않으면 성공
            print(f"[{document_id}] DB 상태 업데이트 성공: {update_response.data}")

        except Exception as db_error:
            raise Exception(f"Supabase DB 상태 업데이트 실패: {db_error}")

        print(f"[{document_id}] ✅ 모든 처리 완료. 상태: completed")
        return {
            "status": "success",
            "message": f"문서 '{filename}' 처리 완료. {len(chunks)}개 청크 저장됨.",
            "chunk_count": len(chunks),
            "document_id": document_id
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
            # DB 업데이트 실패는 치명적이지 않으므로 무시하고 계속 진행

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


def search_similar_documents(query_text: str, limit: int = 5) -> Dict:
    """
    ChromaDB에서 유사한 문서 청크를 검색합니다.
    """
    try:
        # 간단한 텍스트 검색 (임베딩 기반 검색을 위해서는 query_text를 임베딩으로 변환 필요)
        results = vector_collection.query(
            query_texts=[query_text],
            n_results=limit
        )

        return {
            "status": "success",
            "results": {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else []
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


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
                'error_message': None,
                'updated_at': datetime.now().isoformat()
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
        except Exception as e:
            print(f"테스트 중 오류: {e}")


    # asyncio.run(test_processing())
    print("Document processor 모듈이 준비되었습니다.")