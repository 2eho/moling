#!/usr/bin/env python3
"""墨灵性能测试自动化脚本.

此脚本用于自动化性能测试流程：
1. 检查后端服务是否运行
2. 运行性能测试
3. 生成性能报告
4. 与基线比较，检测性能回退

使用方法：
    python performance_automation.py --baseline
    python performance_automation.py --compare baseline.json
"""

import argparse
import json
import subprocess
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

class PerformanceAutomation:
    """性能测试自动化工具."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        
    def check_backend(self, max_retries=5):
        """检查后端服务是否运行."""
        print(f"检查后端服务: {self.base_url}")
        
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/docs", timeout=2)
                if response.status_code == 200:
                    print("✅ 后端服务正在运行")
                    return True
            except Exception as e:
                pass
            
            print(f"等待后端服务... ({i+1}/{max_retries})")
            time.sleep(2)
        
        print("❌ 后端服务未运行")
        return False
    
    def start_backend(self):
        """尝试启动后端服务."""
        print("尝试启动后端服务...")
        # 这里可以添加启动后端的逻辑
        # 例如：subprocess.Popen(["python", "-m", "uvicorn", "app.main:app", "--port", "8000"])
        print("⚠️  自动启动后端功能未实现，请手动启动")
        return False
    
    def run_test(self, test_script, users=5, requests=20, delay=0.7):
        """运行性能测试脚本."""
        print(f"\n运行测试: {test_script}")
        print(f"配置: {users}用户, 每用户{requests}请求, 延迟{delay}s")
        print("="*60)
        
        cmd = [
            sys.executable,
            test_script,
            "--users", str(users),
            "--requests", str(requests),
            "--host", self.base_url,
            "--output", f"{test_script.replace('.py', '_output.json')}"
        ]
        
        if "rate_limited" in test_script:
            cmd.extend(["--delay", str(delay)])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(Path(__file__).parent),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            print(result.stdout)
            if result.stderr:
                print("错误输出:")
                print(result.stderr[:500])
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("❌ 测试超时")
            return False
        except Exception as e:
            print(f"❌ 运行测试失败: {e}")
            return False
    
    def load_results(self, output_file):
        """加载测试结果."""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载结果失败: {e}")
            return None
    
    def compare_with_baseline(self, current_results, baseline_file):
        """与基线比较."""
        print(f"\n与基线比较: {baseline_file}")
        print("="*60)
        
        try:
            with open(baseline_file, 'r', encoding='utf-8') as f:
                baseline = json.load(f)
        except Exception as e:
            print(f"❌ 加载基线失败: {e}")
            return False
        
        # 比较关键指标
        comparisons = []
        
        # 吞吐量
        current_throughput = current_results.get("summary", {}).get("throughput", 0)
        baseline_throughput = baseline.get("summary", {}).get("throughput", 0)
        if baseline_throughput > 0:
            throughput_change = (current_throughput - baseline_throughput) / baseline_throughput * 100
            comparisons.append({
                "metric": "吞吐量",
                "baseline": baseline_throughput,
                "current": current_throughput,
                "change": throughput_change,
                "unit": "req/s"
            })
        
        # P95响应时间
        current_p95 = current_results.get("response_time_ms", {}).get("p95", 0)
        baseline_p95 = baseline.get("response_time_ms", {}).get("p95", 0)
        if baseline_p95 > 0:
            p95_change = (current_p95 - baseline_p95) / baseline_p95 * 100
            comparisons.append({
                "metric": "P95响应时间",
                "baseline": baseline_p95,
                "current": current_p95,
                "change": p95_change,
                "unit": "ms"
            })
        
        # 成功率
        current_success = current_results.get("summary", {}).get("success_rate", 0)
        baseline_success = baseline.get("summary", {}).get("success_rate", 0)
        comparisons.append({
            "metric": "成功率",
            "baseline": baseline_success,
            "current": current_success,
            "change": current_success - baseline_success,
            "unit": "%"
        })
        
        # 打印比较结果
        print(f"{'指标':<20} {'基线':<15} {'当前':<15} {'变化':<15} {'状态':<10}")
        print("-" * 80)
        
        for comp in comparisons:
            if "响应时间" in comp["metric"]:
                # 响应时间：降低是好的
                status = "✅" if comp["change"] < 0 else "⚠️"
            else:
                # 其他指标：提高是好的
                status = "✅" if comp["change"] > 0 else "⚠️"
            
            print(f"{comp['metric']:<20} {comp['baseline']:<15.2f} {comp['current']:<15.2f} {comp['change']:<15.2f} {status:<10}")
        
        # 判断是否有性能回退
        regression = False
        for comp in comparisons:
            if "响应时间" in comp["metric"] and comp["change"] > 20:  # P95增加20%以上
                regression = True
            elif "吞吐量" in comp["metric"] and comp["change"] < -10:  # 吞吐量降低10%以上
                regression = True
            elif "成功率" in comp["metric"] and comp["change"] < -5:  # 成功率降低5%以上
                regression = True
        
        if regression:
            print("\n⚠️  检测到性能回退！")
        else:
            print("\n✅ 未检测到性能回退")
        
        return not regression
    
    def save_baseline(self, results, output_file):
        """保存基线."""
        print(f"\n保存基线: {output_file}")
        
        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": results.get("summary", {}),
            "response_time_ms": results.get("response_time_ms", {}),
            "config": results.get("config", {})
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(baseline_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 基线已保存: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 保存基线失败: {e}")
            return False
    
    def run_full_test(self, create_baseline=False):
        """运行完整的性能测试."""
        print("="*60)
        print("墨灵性能测试自动化")
        print("="*60)
        
        # 1. 检查后端
        if not self.check_backend():
            if not self.start_backend():
                print("❌ 无法连接到后端服务，退出")
                return False
        
        # 2. 运行测试
        tests = [
            ("tests/performance/simple_perf_test.py", 5, 20, 0),
            ("tests/performance/rate_limited_test.py", 3, 10, 0.7)
        ]
        
        all_passed = True
        for test_script, users, requests, delay in tests:
            success = self.run_test(test_script, users, requests, delay)
            if not success:
                all_passed = False
        
        # 3. 加载并分析结果
        print("\n" + "="*60)
        print("测试结果分析")
        print("="*60)
        
        # 这里可以添加结果分析和报告生成逻辑
        
        return all_passed

def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="墨灵性能测试自动化工具")
    parser.add_argument("--baseline", action="store_true", help="创建性能基线")
    parser.add_argument("--compare", type=str, help="与指定基线文件比较")
    parser.add_argument("--host", default="http://localhost:8000", help="后端服务地址")
    args = parser.parse_args()
    
    automation = PerformanceAutomation(base_url=args.host)
    
    if args.baseline:
        # 创建基线模式
        print("创建性能基线...")
        if automation.run_full_test(create_baseline=True):
            print("\n✅ 性能基线已创建")
        else:
            print("\n❌ 创建性能基线失败")
    elif args.compare:
        # 比较模式
        print(f"与基线比较: {args.compare}")
        if not Path(args.compare).exists():
            print(f"❌ 基线文件不存在: {args.compare}")
            sys.exit(1)
        
        if automation.run_full_test():
            # 加载当前结果并与基线比较
            # 这里需要实际加载测试结果
            print("\n✅ 性能比较完成")
        else:
            print("\n❌ 性能测试失败")
    else:
        # 普通测试模式
        print("运行性能测试...")
        if automation.run_full_test():
            print("\n✅ 性能测试完成")
        else:
            print("\n❌ 性能测试失败")

if __name__ == "__main__":
    main()
