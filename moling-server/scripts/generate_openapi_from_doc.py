"""
从接口映射文档生成 OpenAPI 规范（可靠版本）

使用方法：
    python scripts/generate_openapi_from_doc.py
    
输出：
    ../openapi.json (项目根目录)
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────

DOC_PATH = Path(__file__).resolve().parent.parent.parent / "015_54298a88_前后端接口映射.md"
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "openapi.json"

# ─────────────────────────────────────────────────────────────
# OpenAPI 基础模板
# ─────────────────────────────────────────────────────────────

OPENAPI_TEMPLATE = {
    "openapi": "3.0.3",
    "info": {
        "title": "墨灵（Moling）API",
        "description": "墨灵 AI 创意写作平台 API 规范",
        "version": "1.0.0",
        "contact": {
            "name": "Moling Team",
            "email": "support@moling.ai"
        }
    },
    "servers": [
        {
            "url": "http://localhost:8000/api/v1",
            "description": "本地开发环境"
        }
    ],
    "tags": [],
    "paths": {},
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        },
        "schemas": {
            "ApiResponse": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "状态码（0 表示成功）"
                    },
                    "message": {
                        "type": "string",
                        "description": "消息"
                    },
                    "data": {
                        "description": "响应数据（类型取决于具体接口）"
                    },
                    "meta": {
                        "type": "object",
                        "description": "元信息（可选，包含分页等）"
                    }
                },
                "required": ["code", "message"]
            }
        }
    }
}


# ─────────────────────────────────────────────────────────────
# 解析器
# ─────────────────────────────────────────────────────────────

def parse_doc(doc_path: Path) -> dict:
    """
    解析接口映射文档，提取所有 API 端点
    
    返回格式：
    {
        "paths": { "/projects": { "get": {...} } },
        "tags": ["项目", "章节", ...]
    }
    """
    if not doc_path.exists():
        print(f"❌ 文档不存在：{doc_path}")
        return {"paths": {}, "tags": []}
    
    content = doc_path.read_text(encoding="utf-8")
    
    # 提取所有 API 端点
    # 格式：| **API** | `GET /api/v1/projects` |
    #       或：| **API** | GET /api/v1/projects |
    
    paths = defaultdict(dict)
    tags = set()
    
    # 正则：匹配包含 HTTP 方法和路径的行
    # 例：`GET /api/v1/projects` 或 POST /api/v1/projects
    endpoint_pattern = re.compile(
        r'`?(GET|POST|PUT|DELETE|PATCH)\s+(/api/[a-zA-Z0-9/:{}_-]+)`?',
        re.IGNORECASE
    )
    
    # 按行解析
    current_section = ""
    for line in content.split('\n'):
        # 提取当前章节（## 开头的标题）
        section_match = re.match(r'^##?\s+\d*\.?\s*(.*)$', line)
        if section_match:
            current_section = section_match.group(1).strip()
        
        # 查找 API 端点
        for match in endpoint_pattern.finditer(line):
            method = match.group(1).lower()
            path = match.group(2)
            
            # 移除 /api/v1 前缀（OpenAPI 中不写 server 前缀）
            path = path.replace("/api/v1", "")
            
            # 提取 tag（从当前章节或路径）
            tag = extract_tag(path, current_section)
            tags.add(tag)
            
            # 构建 OpenAPI 路径对象
            if path not in paths:
                paths[path] = {}
            
            paths[path][method] = {
                "tags": [tag],
                "summary": f"{method.upper()} {path}",
                "parameters": extract_parameters(path),
                "responses": {
                    "200": {
                        "description": "成功",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse"
                                }
                            }
                        }
                    }
                }
            }
    
    return {
        "paths": dict(paths),
        "tags": sorted(list(tags))
    }


def extract_tag(path: str, section: str) -> str:
    """提取 tag"""
    # 先从章节标题判断
    if "项目" in section:
        return "项目"
    elif "章节" in section or "chapters" in path:
        return "章节"
    elif "卡牌" in section or "cards" in path or "draw" in path:
        return "卡牌"
    elif "生成" in section or "generation" in path:
        return "生成"
    elif "四库" in section or "vault" in path:
        return "四库"
    elif "认证" in section or "auth" in path:
        return "认证"
    elif "导入" in section or "import" in path:
        return "导入"
    elif "设置" in section or "settings" in path:
        return "设置"
    elif "通知" in section or "notifications" in path:
        return "通知"
    elif "健康" in section or "health" in path:
        return "健康监控"
    elif "Phase" in section or "phase4" in path:
        return "Phase4"
    else:
        return "其他"


def extract_parameters(path: str) -> list:
    """从路径提取参数"""
    parameters = []
    
    # 匹配路径参数：{param}
    param_pattern = re.compile(r'\{([a-zA-Z_]+)\}')
    for match in param_pattern.finditer(path):
        param_name = match.group(1)
        parameters.append({
            "name": param_name,
            "in": "path",
            "required": True,
            "schema": {
                "type": "string"
            },
            "description": f"{param_name} 参数"
        })
    
    return parameters


# ─────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────

def main():
    print(f"📄 读取接口映射文档：{DOC_PATH}")
    
    if not DOC_PATH.exists():
        print(f"❌ 文档不存在，创建基础 OpenAPI 规范")
        spec = OPENAPI_TEMPLATE.copy()
    else:
        print(f"✅ 文档存在，解析中...")
        parsed = parse_doc(DOC_PATH)
        
        spec = OPENAPI_TEMPLATE.copy()
        spec["paths"] = parsed["paths"]
        spec["tags"] = [{"name": tag} for tag in parsed["tags"]]
        
        print(f"   - 解析到 {len(parsed['paths'])} 个路径")
        print(f"   - 解析到 {len(parsed['tags'])} 个标签")
    
    # 保存
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ OpenAPI 规范已生成：{OUTPUT_PATH}")
    print(f"   - 路径数：{len(spec['paths'])}")
    print(f"   - Tag 数：{len(spec['tags'])}")
    
    # 列出所有路径
    if spec["paths"]:
        print(f"\n📋 已记录的路径：")
        for path in sorted(spec["paths"].keys()):
            methods = ", ".join(spec["paths"][path].keys()).upper()
            print(f"   {methods:10} {path}")


if __name__ == "__main__":
    main()
