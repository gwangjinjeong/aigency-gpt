# llm_poc/supabase_client.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in .env file")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = get_supabase_client()

if __name__ == "__main__":
    try:
        print("Supabase 클라이언트 초기화 성공!")
    except Exception as e:
        print(f"Supabase 클라이언트 초기화 또는 연결 테스트 실패: {e}")