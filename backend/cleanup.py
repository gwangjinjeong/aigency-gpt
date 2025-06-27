# cleanup_data.py - 기존 데이터 정리 스크립트
import os
import shutil
import chromadb
from app.services.supabase_client import supabase
from datetime import datetime
import traceback


def cleanup_all_data():
    """모든 기존 데이터를 정리합니다"""
    print("🧹 기존 데이터 정리를 시작합니다...")

    # 1. ChromaDB 컬렉션 삭제
    cleanup_chromadb()

    # 2. 임시 파일들 정리
    cleanup_temp_files()

    # 3. PDF 캐시 정리
    cleanup_pdf_cache()

    # 4. Supabase documents 테이블 상태 초기화 (선택사항)
    # reset_supabase_documents()  # 주석 해제하여 사용

    print("✅ 모든 데이터 정리가 완료되었습니다!")


def cleanup_chromadb():
    """ChromaDB 컬렉션을 완전히 삭제하고 재생성"""
    try:
        print("🗑️ ChromaDB 컬렉션 정리 중...")

        # ChromaDB 클라이언트 초기화
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection_name = "pdf_document_embeddings"

        try:
            # 기존 컬렉션 삭제
            chroma_client.delete_collection(name=collection_name)
            print(f"   ✅ 기존 컬렉션 '{collection_name}' 삭제 완료")
        except Exception as e:
            print(f"   ℹ️ 컬렉션이 존재하지 않음 또는 삭제 실패: {e}")

        # 새 컬렉션 생성
        new_collection = chroma_client.create_collection(name=collection_name)
        print(f"   ✅ 새 컬렉션 '{collection_name}' 생성 완료")

        # ChromaDB 디렉토리 전체 정리 (선택사항 - 더 확실한 정리)
        chroma_db_path = "./chroma_db"
        if os.path.exists(chroma_db_path):
            print(f"   🗑️ ChromaDB 디렉토리 전체 삭제: {chroma_db_path}")
            shutil.rmtree(chroma_db_path)
            print(f"   ✅ ChromaDB 디렉토리 삭제 완료")

            # 디렉토리 재생성
            os.makedirs(chroma_db_path, exist_ok=True)

            # 새 클라이언트로 컬렉션 재생성
            new_client = chromadb.PersistentClient(path=chroma_db_path)
            new_client.create_collection(name=collection_name)
            print(f"   ✅ 새 ChromaDB 클라이언트 및 컬렉션 생성 완료")

    except Exception as e:
        print(f"   ❌ ChromaDB 정리 중 오류: {e}")
        traceback.print_exc()


def cleanup_temp_files():
    """임시 파일들을 정리"""
    try:
        print("🗑️ 임시 파일 정리 중...")

        temp_patterns = [
            "/tmp/*.pdf",
            "/var/folders/*/T/tmp*.pdf",
            "./temp_*.pdf",
            "./*.pdf"  # 현재 디렉토리의 PDF 파일들
        ]

        import glob
        total_deleted = 0

        for pattern in temp_patterns:
            try:
                files = glob.glob(pattern)
                for file_path in files:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"   ✅ 삭제: {file_path}")
                            total_deleted += 1
                        except Exception as e:
                            print(f"   ⚠️ 삭제 실패: {file_path} - {e}")
            except Exception as e:
                print(f"   ⚠️ 패턴 검색 실패: {pattern} - {e}")

        # /tmp 디렉토리의 특정 패턴 파일들 삭제
        tmp_dir = "/tmp"
        if os.path.exists(tmp_dir):
            for filename in os.listdir(tmp_dir):
                if filename.endswith('.pdf') and ('tmp' in filename or len(filename) == 40):  # UUID 길이
                    file_path = os.path.join(tmp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"   ✅ /tmp 삭제: {filename}")
                        total_deleted += 1
                    except Exception as e:
                        print(f"   ⚠️ /tmp 삭제 실패: {filename} - {e}")

        print(f"   ✅ 총 {total_deleted}개 임시 파일 삭제 완료")

    except Exception as e:
        print(f"   ❌ 임시 파일 정리 중 오류: {e}")


def cleanup_pdf_cache():
    """PDF 캐시 디렉토리 정리"""
    try:
        print("🗑️ PDF 캐시 정리 중...")

        cache_dir = "./pdf_cache"

        if os.path.exists(cache_dir):
            # 캐시 디렉토리 내용 삭제
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"   ✅ 캐시 파일 삭제: {filename}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"   ✅ 캐시 디렉토리 삭제: {filename}")
                except Exception as e:
                    print(f"   ⚠️ 캐시 삭제 실패: {filename} - {e}")

            # 캐시 디렉토리 자체 삭제 후 재생성
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            print(f"   ✅ PDF 캐시 디렉토리 초기화 완료: {cache_dir}")
        else:
            print(f"   ℹ️ PDF 캐시 디렉토리가 존재하지 않습니다: {cache_dir}")

    except Exception as e:
        print(f"   ❌ PDF 캐시 정리 중 오류: {e}")


def reset_supabase_documents():
    """Supabase documents 테이블의 상태를 초기화 (선택사항)"""
    try:
        print("🗑️ Supabase documents 테이블 상태 초기화 중...")

        # 모든 문서 상태를 'pending'으로 되돌리기
        response = supabase.from_('documents').update({
            'status': 'pending',
            'processed_at': None
        }).neq('id', '').execute()  # 모든 레코드 업데이트

        print(f"   ✅ {len(response.data) if response.data else 0}개 문서 상태를 'pending'으로 초기화")

    except Exception as e:
        print(f"   ❌ Supabase 테이블 초기화 중 오류: {e}")


def cleanup_specific_document(document_id: str):
    """특정 문서의 데이터만 정리"""
    try:
        print(f"🗑️ 문서 {document_id} 데이터 정리 중...")

        # 1. ChromaDB에서 해당 문서 벡터 삭제
        try:
            chroma_client = chromadb.PersistentClient(path="./chroma_db")
            collection = chroma_client.get_collection(name="pdf_document_embeddings")

            results = collection.get(where={"document_id": document_id})
            if results["ids"]:
                collection.delete(ids=results["ids"])
                print(f"   ✅ ChromaDB에서 {len(results['ids'])}개 청크 삭제")
            else:
                print(f"   ℹ️ ChromaDB에 해당 문서 데이터 없음")

        except Exception as e:
            print(f"   ⚠️ ChromaDB 삭제 실패: {e}")

        # 2. 캐시 파일 삭제
        cache_file = f"./pdf_cache/{document_id}.pdf"
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"   ✅ 캐시 파일 삭제: {cache_file}")
        else:
            print(f"   ℹ️ 캐시 파일 없음: {cache_file}")

        # 3. 임시 파일들 삭제
        temp_patterns = [
            f"/tmp/{document_id}.pdf",
            f"/tmp/{document_id}_*.pdf"
        ]

        import glob
        for pattern in temp_patterns:
            files = glob.glob(pattern)
            for file_path in files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"   ✅ 임시 파일 삭제: {file_path}")

        # 4. Supabase 상태 초기화
        try:
            supabase.from_('documents').update({
                'status': 'pending',
                'processed_at': None
            }).eq('id', document_id).execute()
            print(f"   ✅ Supabase 상태 'pending'으로 초기화")
        except Exception as e:
            print(f"   ⚠️ Supabase 상태 초기화 실패: {e}")

        print(f"✅ 문서 {document_id} 정리 완료")

    except Exception as e:
        print(f"❌ 문서 {document_id} 정리 중 오류: {e}")


def get_cleanup_status():
    """현재 데이터 상태 확인"""
    print("📊 현재 데이터 상태 확인 중...")

    # ChromaDB 상태
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_collection(name="pdf_document_embeddings")
        count_result = collection.count()
        print(f"   📄 ChromaDB 벡터 수: {count_result}")
    except Exception as e:
        print(f"   📄 ChromaDB: 컬렉션 없음 또는 오류 - {e}")

    # PDF 캐시 상태
    cache_dir = "./pdf_cache"
    if os.path.exists(cache_dir):
        cache_files = len([f for f in os.listdir(cache_dir) if f.endswith('.pdf')])
        print(f"   💾 PDF 캐시 파일 수: {cache_files}")
    else:
        print(f"   💾 PDF 캐시: 디렉토리 없음")

    # 임시 파일 상태
    import glob
    temp_files = len(glob.glob("/tmp/*.pdf"))
    print(f"   🗂️ /tmp PDF 파일 수: {temp_files}")

    # Supabase documents 상태
    try:
        response = supabase.from_('documents').select('status').execute()
        if response.data:
            from collections import Counter
            status_counts = Counter([doc['status'] for doc in response.data])
            print(f"   🗃️ Supabase 문서 상태: {dict(status_counts)}")
        else:
            print(f"   🗃️ Supabase: 문서 없음")
    except Exception as e:
        print(f"   🗃️ Supabase 조회 실패: {e}")


if __name__ == "__main__":
    print("🧹 데이터 정리 스크립트")
    print("=" * 50)

    # 현재 상태 확인
    get_cleanup_status()
    print()

    # 사용자 확인
    choice = input("전체 데이터를 정리하시겠습니까? (y/N): ").strip().lower()

    if choice == 'y':
        cleanup_all_data()
        print()
        print("정리 후 상태:")
        get_cleanup_status()
    else:
        print("정리가 취소되었습니다.")

        # 특정 문서 정리 옵션
        doc_id = input("특정 문서 ID를 정리하시겠습니까? (문서 ID 입력 또는 엔터): ").strip()
        if doc_id:
            cleanup_specific_document(doc_id)

# 개별 함수 사용 예시:
# cleanup_all_data()  # 전체 정리
# cleanup_specific_document("31fe9357-4ea3-41ae-a6e0-14e50506e119")  # 특정 문서 정리
# get_cleanup_status()  # 상태 확인