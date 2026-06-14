#!/usr/bin/env python3
"""
Moling Frontend Automated Test Suite
Tests UI rendering and user flows using requests (since backend is down)
"""

import requests
from bs4 import BeautifulSoup
import time
import os

BASE_URL = "http://localhost:3000"
REPORT_PATH = r"C:\Users\Admin\Desktop\新建文件夹 (2)\moling_test_report.md"

def test_page_load():
    """Test if frontend pages load correctly."""
    print("\n=== 测试1：页面加载测试 ===")
    
    pages = [
        ("/", "首页/Landing Page"),
        ("/login", "登录页"),
        ("/register", "注册页"),
        ("/workspace", "工作区（需要登录）"),
    ]
    
    results = []
    for path, name in pages:
        url = BASE_URL + path
        try:
            resp = requests.get(url, timeout=5, allow_redirects=True)
            status = resp.status_code
            redirect = resp.url != url
            
            # Check if page has content
            soup = BeautifulSoup(resp.text, 'html.parser')
            has_title = soup.title is not None
            has_content = len(resp.text) > 1000
            
            results.append({
                'page': path,
                'name': name,
                'status': status,
                'redirect': redirect,
                'has_title': has_title,
                'has_content': has_content,
                'success': status == 200 and has_content
            })
            
            print(f"  {path:20s} - Status: {status}, Redirect: {redirect}, Has Content: {has_content}")
        except Exception as e:
            print(f"  {path:20s} - ERROR: {str(e)}")
            results.append({'page': path, 'success': False, 'error': str(e)})
    
    return results

def test_api_endpoints():
    """Test API endpoints (expect failure since backend is down)."""
    print("\n=== 测试2：API端点测试（后端未运行） ===")
    
    endpoints = [
        ("/api/v1/health", "健康检查"),
        ("/api/v1/auth/register", "注册"),
        ("/api/v1/auth/login", "登录"),
    ]
    
    for path, name in endpoints:
        url = "http://localhost:8000" + path
        try:
            resp = requests.get(url, timeout=2)
            print(f"  {name:20s} - Status: {resp.status_code} (意外：后端不应该运行)")
        except:
            print(f"  {name:20s} - 连接失败 (预期：后端未运行)")
    
    return True

def test_static_assets():
    """Test if static assets (CSS, JS) are loaded."""
    print("\n=== 测试3：静态资源测试 ===")
    
    try:
        resp = requests.get(BASE_URL, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find script and link tags
        scripts = soup.find_all('script', src=True)
        links = soup.find_all('link', rel='stylesheet')
        
        print(f"  找到 {len(scripts)} 个脚本标签")
        print(f"  找到 {len(links)} 个样式标签")
        
        # Check if JS bundle exists
        for script in scripts:
            src = script['src']
            if 'main' in src or 'bundle' in src:
                print(f"  JS Bundle: {src}")
        
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def generate_report(results):
    """Generate test report."""
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    print("\n## 执行摘要")
    total = len(results)
    passed = sum(1 for r in results if r.get('success', False))
    print(f"- 总测试数: {total}")
    print(f"- 通过: {passed}")
    print(f"- 失败: {total - passed}")
    
    print("\n## 详细结果")
    for r in results:
        status = "✅ PASS" if r.get('success', False) else "❌ FAIL"
        print(f"{status} - {r.get('name', r.get('page', 'Unknown'))}")
        if not r.get('success', False) and 'error' in r:
            print(f"      错误: {r['error']}")
    
    print("\n## 问题与建议")
    print("1. ❌ 后端未运行 - 需要修复Python文件编码问题")
    print("2. ⚠️  无法进行完整前后端集成测试")
    print("3. 📝 建议：将Python文件中的中文注释改为英文，或使用UTF-8编码保存")
    print("4. 🔧 临时方案：使用Python 3.8-3.10（默认GBK编码）运行后端")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    print("开始前端自动化测试...")
    print(f"前端URL: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    results = []
    results.extend(test_page_load())
    test_api_endpoints()
    test_static_assets()
    
    # Generate report
    generate_report(results)
    
    # Save report to file
    report_content = f"""# 墨灵项目测试报告

**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 测试环境
- **前端**: http://localhost:3000 (运行中)
- **后端**: http://localhost:8000 (未运行 - 编码问题)
- **测试工具**: Python + requests + BeautifulSoup

## 测试结果摘要
- **总测试数**: {len(results)}
- **通过**: {sum(1 for r in results if r.get('success', False))}
- **失败**: {sum(1 for r in results if not r.get('success', False))}

## 详细测试结果

### 测试1：页面加载测试
"""
    
    for r in results:
        status = "✅ PASS" if r.get('success', False) else "❌ FAIL"
        report_content += f"- {status} {r.get('name', r.get('page', 'Unknown'))}\n"
        if not r.get('success', False) and 'error' in r:
            report_content += f"  - 错误: {r['error']}\n"
    
    report_content += """
## 主要问题

### 1. 后端无法启动 (P0 - 阻塞)
**问题描述**: Python文件编码问题导致后端无法启动
- 原始文件使用GBK编码保存
- Python 3.13尝试用UTF-8读取失败
- 多次尝试转换编码均失败

**错误信息**:
```
SyntaxError: unterminated string literal (detected at line 85)
```

**可能原因**:
1. 文件在创建时使用GBK编码
2. 中文字符在编码转换过程中损坏
3. Python 3.13默认UTF-8，无法读取GBK文件

**建议修复方案**:
1. **方案A**: 使用Python 3.8-3.10运行（默认GBK编码）
2. **方案B**: 批量删除所有中文注释，改为英文
3. **方案C**: 使用iconv或专业工具转换编码
4. **方案D**: 重新创建项目，所有注释使用英文

### 2. 无法进行完整测试 (P1 - 影响)
由于后端未运行，以下测试无法执行：
- 用户注册/登录流程
- 项目管理功能
- 章节编辑功能
- 卡牌抽取功能
- 世界观库功能
- 生成管线功能

## 建议下一步行动

1. **立即行动**: 修复后端编码问题（选择上述方案之一）
2. **测试计划**: 后端修复后，执行完整的前后端的集成测试
3. **测试范围**: 参考原始测试方案（Phase 1-5）

## 附录：完整测试方案

### Phase 1: 后端API测试 (60分钟)
- 认证模块：13个测试用例
- 项目管理：12个测试用例
- 章节管理：12个测试用例
- 卡牌系统：9个测试用例
- 世界观库：10个测试用例
- 生成管线：8个测试用例

### Phase 2: 前端UI测试 (90分钟)
- 用户注册流程
- 用户登录流程
- 创建项目流程
- 章节编辑流程
- 卡牌抽取流程
- 响应式布局测试

### Phase 3: 数据库完整性测试 (30分钟)
- 外键约束验证
- 唯一约束验证
- 级联删除验证

### Phase 4: 性能测试 (30分钟)
- API响应时间测试
- 并发用户测试
- 数据库查询性能

### Phase 5: 安全测试 (30分钟)
- SQL注入测试
- XSS攻击测试
- CSRF攻击测试
- JWT安全测试

---

**报告生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n✅ 测试完成！报告已保存到: {REPORT_PATH}")
