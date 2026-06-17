"""验证 ASGI ResponseFormatMiddleware 是否能正确包装响应。"""
import json
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.middleware.response_format import ResponseFormatMiddleware

# 创建一个测试 app
app = FastAPI()
app.add_middleware(ResponseFormatMiddleware, version="test.1.0")

@app.get("/test")
def test_endpoint():
    return {"message": "hello", "value": 42}

@app.get("/test-login")
def test_login():
    return {
        "access_token": "eyJtest",
        "token_type": "bearer",
        "user": {"id": "123", "email": "test@test.com"}
    }

# 使用 httpx 的 TestClient
from fastapi.testclient import TestClient
client = TestClient(app)

# Test 1
r1 = client.get("/test")
print(f"=== Test 1: /test ===")
print(f"Status: {r1.status_code}")
data1 = r1.json()
print(f"Body: {json.dumps(data1, ensure_ascii=False, indent=2)}")
assert "code" in data1, "FAIL: /test 没有被包装"
assert data1["code"] == 0
assert data1["data"]["message"] == "hello"
print("PASS\n")

# Test 2
r2 = client.get("/test-login")
print(f"=== Test 2: /test-login ===")
print(f"Status: {r2.status_code}")
data2 = r2.json()
print(f"Body: {json.dumps(data2, ensure_ascii=False, indent=2)}")
assert "code" in data2, "FAIL: /test-login 没有被包装"
assert data2["data"]["access_token"] == "eyJtest"
print("PASS\n")

print("=== ALL PASS ===")
