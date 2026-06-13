"""启动后端服务并运行性能测试."""

import subprocess
import time
import requests
import sys
import os

def start_backend():
    """启动后端服务."""
    print("正在启动后端服务...")
    # 使用subprocess启动uvicorn
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd="C:\\Users\\Admin\\Desktop\\MolingProject\\moling-server",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待后端启动
    print("等待后端服务启动...")
    time.sleep(5)
    
    # 检查后端是否启动
    for i in range(10):
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("✅ 后端服务已启动")
                return backend_process
        except:
            pass
        print(f"等待中... ({i+1}/10)")
        time.sleep(2)
    
    print("❌ 后端服务启动失败")
    return None

def run_simple_test():
    """运行简单性能测试."""
    print("\n" + "="*60)
    print("开始运行性能测试...")
    print("="*60)
    
    # 运行simple_perf_test.py
    result = subprocess.run(
        [sys.executable, "tests/performance/simple_perf_test.py", 
         "--users", "5", "--requests", "20", "--host", "http://localhost:8000"],
        cwd="C:\\Users\\Admin\\Desktop\\MolingProject\\moling-server",
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode == 0

def run_rate_limited_test():
    """运行速率限制测试."""
    print("\n" + "="*60)
    print("开始运行速率限制测试...")
    print("="*60)
    
    # 运行rate_limited_test.py
    result = subprocess.run(
        [sys.executable, "tests/performance/rate_limited_test.py",
         "--users", "3", "--requests", "10", "--delay", "0.7", "--host", "http://localhost:8000"],
        cwd="C:\\Users\\Admin\\Desktop\\MolingProject\\moling-server",
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    # 启动后端
    backend = start_backend()
    
    if backend is None:
        print("无法启动后端服务，退出测试")
        sys.exit(1)
    
    try:
        # 运行测试
        print("\n1. 运行简单性能测试...")
        success1 = run_simple_test()
        
        print("\n2. 运行速率限制测试...")
        success2 = run_rate_limited_test()
        
        if success1 and success2:
            print("\n✅ 所有测试完成")
        else:
            print("\n⚠️ 部分测试失败")
        
    finally:
        # 关闭后端服务
        print("\n正在关闭后端服务...")
        backend.terminate()
        backend.wait()
        print("后端服务已关闭")
