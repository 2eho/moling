"""
导出 FastAPI 的 OpenAPI 规范到静态文件

使用方法：
    python scripts/export_openapi.py           # 导出到 ../../openapi.json
    python scripts/export_openapi.py --yaml    # 同时导出 YAML 格式
    python scripts/export_openapi.py --check   # 仅检查是否与已提交的文件一致
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app


def export_openapi(output_path: Path, format: str = "json"):
    """导出 OpenAPI 规范"""
    openapi_schema = app.openapi()

    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
        print(f"✅ OpenAPI 规范已导出到：{output_path}")

    elif format == "yaml":
        try:
            import yaml
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(openapi_schema, f, allow_unicode=True, sort_keys=False)
            print(f"✅ OpenAPI 规范已导出到：{output_path}")
        except ImportError:
            print("❌ 需要安装 PyYAML：pip install pyyaml")
            sys.exit(1)


def check_openapi(snapshot_path: Path):
    """检查当前 OpenAPI 规范是否与快照一致"""
    if not snapshot_path.exists():
        print(f"❌ 快照文件不存在：{snapshot_path}")
        sys.exit(1)

    openapi_schema = app.openapi()
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    if openapi_schema == snapshot:
        print("✅ OpenAPI 规范与快照一致")
        sys.exit(0)
    else:
        print("❌ OpenAPI 规范与快照不一致！")
        print("   请运行：python scripts/export_openapi.py")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="导出 FastAPI OpenAPI 规范")
    parser.add_argument("--yaml", action="store_true", help="同时导出 YAML 格式")
    parser.add_argument("--check", action="store_true", help="检查是否与快照一致")
    parser.add_argument("--output", default="../../openapi.json", help="输出路径")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()

    if args.check:
        check_openapi(output_path)
    else:
        export_openapi(output_path)
        if args.yaml:
            yaml_path = output_path.with_suffix(".yaml")
            export_openapi(yaml_path, format="yaml")


if __name__ == "__main__":
    main()
