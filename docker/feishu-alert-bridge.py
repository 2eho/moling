#!/usr/bin/env python3
# ==============================================================================
# Feishu Alert Bridge — AlertManager → 飞书富文本卡片
# ==============================================================================
# 部署为独立容器，接收 AlertManager webhook，
# 转换为飞书消息卡片，每条消息就是完整的故障诊断报告。
#
# 飞书卡片格式: https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-components/overview
# ==============================================================================

import os
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests
from flask import Flask, request, jsonify

# ═══════════════════════════════════════════════════════════════
# 配置（通过环境变量）
# ═══════════════════════════════════════════════════════════════
FEISHU_WEBHOOK_URL: str = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET: str = os.environ.get("FEISHU_SECRET", "")  # 飞书签名校验（可选）
GRAFANA_BASE_URL: str = os.environ.get("GRAFANA_BASE_URL", "http://124.222.163.79:3001")
TZ = timezone(timedelta(hours=8))  # 北京时间

app = Flask(__name__)


# ═══════════════════════════════════════════════════════════════
# 飞书签名（安全校验，可选）
# ═══════════════════════════════════════════════════════════════
def _gen_sign(timestamp: int) -> str:
    """生成飞书签名"""
    if not FEISHU_SECRET:
        return ""
    string_to_sign = f"{timestamp}\n{FEISHU_SECRET}"
    hmac_code = hmac.new(
        FEISHU_SECRET.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# 颜色映射
# ═══════════════════════════════════════════════════════════════
SEVERITY_COLORS: dict[str, str] = {
    "critical": "red",
    "warning": "yellow",
    "info": "blue",
    "resolved": "green",
}

SEVERITY_ICONS: dict[str, str] = {
    "critical": "🔴",
    "warning": "🟡",
    "info": "🔵",
    "resolved": "🟢",
}

SEVERITY_TITLES: dict[str, str] = {
    "critical": "严重告警",
    "warning": "警告提醒",
    "info": "提示信息",
    "resolved": "已恢复",
}


# ═══════════════════════════════════════════════════════════════
# 飞书卡片构建
# ═══════════════════════════════════════════════════════════════
def build_feishu_card(
    status: str,        # "firing" or "resolved"
    alerts: list[dict],
    group_labels: dict,
) -> dict:
    """将一组告警构建为飞书消息卡片"""

    is_resolved = status == "resolved"
    severity = "resolved" if is_resolved else alerts[0].get("labels", {}).get("severity", "warning")
    color = SEVERITY_COLORS.get(severity, "blue")
    icon = SEVERITY_ICONS.get(severity, "🔵")
    title_prefix = SEVERITY_TITLES.get(severity, "通知")

    # 标题
    alert_count = len(alerts)
    alert_names = ", ".join(
        set(a.get("annotations", {}).get("title", a.get("labels", {}).get("alertname", "未知"))
             for a in alerts)
    )
    title = f"{icon} [{title_prefix}] {alert_names}"
    if alert_count > 1:
        title += f"（共 {alert_count} 条）"

    # 时间
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 构建卡片内容
    elements: list[dict] = []

    # ── 头部标题 ──
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**{title}**"}
    })

    # ── 分隔线 ──
    elements.append({"tag": "hr"})

    # ── 时间信息 ──
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"⏰ 触发时间: {now_str}"}
    })

    # ── 每条告警详情 ──
    for i, alert in enumerate(alerts):
        annotations = alert.get("annotations", {})
        labels = alert.get("labels", {})

        if alert_count > 1:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**━━━ 告警 {i+1}/{alert_count} ━━━**"}
            })

        # 当前状态
        current = annotations.get("current_status", "—")
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"📊 **当前状态**\n{current}"}
        })

        # 影响范围
        impact = annotations.get("impact", "")
        if impact:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"⚠️ **影响范围**\n{impact}"}
            })

        # 处理步骤（最重要！）
        runbook = annotations.get("runbook", "")
        if runbook:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"🔧 **处理步骤**\n{runbook}"}
            })

        # Grafana 链接
        grafana_link = annotations.get("grafana_link", "")
        if grafana_link:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📈 [点击查看 Grafana 大盘]({grafana_link})"
                }
            })

    # ── 底部动作按钮 ──
    actions: list[dict] = []

    # Grafana 链接按钮
    first_grafana = alerts[0].get("annotations", {}).get("grafana_link", "")
    if first_grafana:
        actions.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📈 查看监控大盘"},
            "type": "default",
            "url": first_grafana,
        })

    # 服务器 SSH（仅参考，无法点击直连）
    actions.append({
        "tag": "button",
        "text": {"tag": "plain_text", "content": "🚀 GitHub Actions"},
        "type": "default",
        "url": "https://github.com/2eho/moling/actions",
    })

    # ── 卡片结构 ──
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": elements,
    }

    if actions:
        # 飞书 action 布局：每个按钮独立一行
        for action in actions:
            elements.append({
                "tag": "action",
                "actions": [action],
            })

    return card


# ═══════════════════════════════════════════════════════════════
# 飞书发送
# ═══════════════════════════════════════════════════════════════
def send_to_feishu(card: dict) -> bool:
    """发送卡片消息到飞书"""
    if not FEISHU_WEBHOOK_URL:
        print("[feishu-bridge] FEISHU_WEBHOOK_URL 未配置，跳过发送")
        return False

    timestamp = int(time.time())
    sign = _gen_sign(timestamp)

    payload = {
        "timestamp": str(timestamp),
        "sign": sign,
        "msg_type": "interactive",
        "card": card,
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            print(f"[feishu-bridge] 飞书发送成功: StatusMessage={result.get('StatusMessage')}")
            return True
        else:
            print(f"[feishu-bridge] 飞书发送失败: code={result.get('code')} msg={result.get('msg')}")
            return False
    except Exception as e:
        print(f"[feishu-bridge] 飞书请求异常: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# AlertManager Webhook 接收
# ═══════════════════════════════════════════════════════════════
@app.route("/alerts", methods=["POST"])
def handle_alerts():
    """接收 AlertManager webhook v4 格式"""
    data: dict = request.get_json(force=True)

    if not data:
        return jsonify({"status": "error", "message": "empty payload"}), 400

    status: str = data.get("status", "firing")
    alerts: list[dict] = data.get("alerts", [])
    group_labels: dict = data.get("groupLabels", {})

    if not alerts:
        return jsonify({"status": "ok", "message": "no alerts"}), 200

    print(f"[feishu-bridge] 收到 {len(alerts)} 条告警, status={status}")

    # 构建飞书卡片
    card = build_feishu_card(status=status, alerts=alerts, group_labels=group_labels)

    # 发送
    success = send_to_feishu(card)

    return jsonify({
        "status": "ok" if success else "error",
        "alerts_processed": len(alerts),
        "feishu_sent": success,
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now(TZ).isoformat()})


# ═══════════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("[feishu-bridge] 启动中...")
    print(f"[feishu-bridge] FEISHU_WEBHOOK_URL: {'已配置' if FEISHU_WEBHOOK_URL else '未配置!'}")
    print(f"[feishu-bridge] 监听端口: 9094")
    app.run(host="0.0.0.0", port=9094, debug=False)
