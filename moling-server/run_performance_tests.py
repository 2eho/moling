"""简单的性能测试启动脚本."""

import subprocess
import time
import requests
import sys
import os

def check_backend():
    """检查后端是否在运行."""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    """启动后端服务."""
    print("正在启动后端服务...")
    try:
        # 使用subprocess启动后端
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="C:\\Users\\Admin\\Desktop\\MolingProject\\moling-server"
        )
        
        # 等待后端启动
        for i in range(10):
            if check_backend():
                print("✅ 后端服务已启动")
                return process
            print(f"等待后端启动... ({i+1}/10)")
            time.sleep(2)
        
        print("❌ 后端服务启动超时")
        return None
    except Exception as e:
        print(f"❌ 启动后端失败: {e}")
        return None

def run_test(script_name, description):
    """运行测试脚本."""
    print(f"\n{'='*60}")
    print(f"运行 {description}...")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name, 
             "--users", "5", "--requests", "20", 
             "--host", "http://localhost:8000"],
            cwd="C:\\Users\\Admin\\Desktop\\MolingProject\\moling-server",
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 运行测试失败: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("墨灵性能测试工具")
    print("="*60)
    
    # 检查后端是否在运行
    if not check_backend():
        print("后端服务未运行，正在启动...")
        backend_process = start_backend()
        if backend_process is None:
            print("无法启动后端服务，退出")
            sys.exit(1)
    else:
        print("✅ 后端服务已在运行")
        backend_process = None
    
    # 运行测试
    results = []
    
    # 测试1: 简单性能测试
    success1 = run_test("tests/performance/simple_perf_test.py", "简单性能测试")
    results.append(("简单性能测试", success1))
    
    # 测试2: 速率限制测试
    success2 = run_test("tests/performance/rate_limited_test.py", "速率限制测试")
    results.append(("速率限制测试", success2))
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    # 关闭后端服务
    if backend_process:
        print("\n正在关闭后端服务...")
        backend_process.terminate()
        backend_process.wait()
        print("后端服务已关闭")
    
    # 生成性能报告
    print("\n正在生成性能报告...")
    if os.path.exists("performance_report.json"):
        print("✅ 性能报告已生成: performance_report.json")
    if os.path.exists("rate_limited_report.json"):
        print("✅ 速率限制报告已生成: rate_limited_report.json")
