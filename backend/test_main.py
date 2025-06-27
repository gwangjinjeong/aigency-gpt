# test_backend.py - 백엔드 서버 테스트 스크립트

import requests
import json


def test_backend_connection():
    """백엔드 서버 연결 테스트"""
    base_urls = [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'http://0.0.0.0:8080'
    ]

    for url in base_urls:
        try:
            print(f"\n🔍 Testing connection to {url}")

            # 기본 엔드포인트 테스트
            response = requests.get(f"{url}/", timeout=5)
            print(f"✅ Root endpoint: {response.status_code} - {response.json()}")

            # Health check 테스트
            response = requests.get(f"{url}/health", timeout=5)
            print(f"✅ Health check: {response.status_code} - {response.json()}")

            # Documents 엔드포인트 테스트
            response = requests.get(f"{url}/documents", timeout=5)
            print(f"✅ Documents endpoint: {response.status_code}")

            print(f"🎉 Backend server is running at {url}")
            return url

        except requests.exceptions.ConnectionError:
            print(f"❌ Connection refused to {url}")
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout connecting to {url}")
        except Exception as e:
            print(f"❌ Error connecting to {url}: {e}")

    print("\n❌ No backend server found. Please start the FastAPI server.")
    return None


def test_cors():
    """CORS 설정 테스트"""
    url = "http://localhost:8000"
    headers = {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type'
    }

    try:
        response = requests.options(f"{url}/documents", headers=headers, timeout=5)
        print(f"\n🔍 CORS preflight test: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ CORS test failed: {e}")


if __name__ == "__main__":
    print("🚀 Backend Server Test")
    print("=" * 50)

    # 연결 테스트
    working_url = test_backend_connection()

    if working_url:
        # CORS 테스트
        test_cors()

        print(f"\n✅ Backend is ready!")
        print(f"📝 Use this URL in your frontend: {working_url}")
    else:
        print("\n🔧 Troubleshooting steps:")
        print("1. cd backend")
        print("2. pip install -r requirement.txt")
        print("3. python main.py")
        print("4. Check if port 8000 is available")