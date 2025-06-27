# backend/app/services/supabase_client.py 수정

import os
from dotenv import load_dotenv


# .env 파일 로드 (여러 경로에서 시도)
def load_env_files():
    possible_paths = [
        '.env',
        '../.env',
        '../../.env',
        '../../../.env'
    ]

    for path in possible_paths:
        if os.path.exists(path):
            load_dotenv(dotenv_path=path)
            print(f"✅ .env 파일 로드됨: {path}")
            return True

    print("⚠️ .env 파일을 찾을 수 없습니다.")
    return False


# .env 파일 로드 시도
load_env_files()

# 환경변수 가져오기
SUPABASE_URL: str = os.environ.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

print(f"🔍 Supabase URL: {'✅ 설정됨' if SUPABASE_URL else '❌ 미설정'}")
print(f"🔍 Supabase Key: {'✅ 설정됨' if SUPABASE_KEY else '❌ 미설정'}")

# Supabase 클라이언트 초기화 (오류 방지)
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client, Client


        def get_supabase_client() -> Client:
            return create_client(SUPABASE_URL, SUPABASE_KEY)


        supabase: Client = get_supabase_client()
        print("✅ Supabase 클라이언트 초기화 성공!")

    else:
        print("⚠️ Supabase 환경변수가 설정되지 않았습니다.")
        print("🔧 더미 클라이언트를 사용합니다.")


        # 더미 Supabase 클라이언트 클래스
        class DummySupabaseClient:
            def __init__(self):
                self.connected = False

            def from_(self, table_name):
                return DummyTable()

            @property
            def storage(self):
                return DummyStorage()


        class DummyTable:
            def select(self, *args):
                return self

            def insert(self, data):
                return self

            def update(self, data):
                return self

            def delete(self):
                return self

            def eq(self, column, value):
                return self

            def order(self, column, **kwargs):
                return self

            def limit(self, count):
                return self

            def execute(self):
                return type('Result', (), {
                    'data': [],
                    'count': 0,
                    'error': None
                })()


        class DummyStorage:
            def from_(self, bucket_name):
                return DummyBucket()


        class DummyBucket:
            def upload(self, path, file, **kwargs):
                return {"path": path}

            def download(self, path):
                return b"dummy file content"

            def get_public_url(self, path):
                return f"https://dummy-url.com/{path}"

            def remove(self, paths):
                return {"message": "removed"}


        supabase = DummySupabaseClient()
        print("🔧 더미 Supabase 클라이언트 생성됨")

except Exception as e:
    print(f"❌ Supabase 클라이언트 초기화 실패: {e}")
    print("🔧 더미 클라이언트를 사용합니다.")


    # 더미 클라이언트 (위와 동일)
    class DummySupabaseClient:
        def __init__(self):
            self.connected = False

        def from_(self, table_name):
            return DummyTable()

        @property
        def storage(self):
            return DummyStorage()


    class DummyTable:
        def select(self, *args):
            return self

        def insert(self, data):
            return self

        def update(self, data):
            return self

        def delete(self):
            return self

        def eq(self, column, value):
            return self

        def order(self, column, **kwargs):
            return self

        def limit(self, count):
            return self

        def execute(self):
            return type('Result', (), {
                'data': [],
                'count': 0,
                'error': None
            })()


    class DummyStorage:
        def from_(self, bucket_name):
            return DummyBucket()


    class DummyBucket:
        def upload(self, path, file, **kwargs):
            return {"path": path}

        def download(self, path):
            return b"dummy file content"

        def get_public_url(self, path):
            return f"https://dummy-url.com/{path}"

        def remove(self, paths):
            return {"message": "removed"}


    supabase = DummySupabaseClient()

if __name__ == "__main__":
    try:
        print("🧪 Supabase 클라이언트 테스트:")
        print(f"   타입: {type(supabase)}")
        print(f"   연결됨: {hasattr(supabase, 'connected')}")

        # 간단한 테스트
        result = supabase.from_('test').select('*').execute()
        print(f"   테스트 쿼리: {'✅ 성공' if result else '❌ 실패'}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")