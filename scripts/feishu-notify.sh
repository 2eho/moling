#!/bin/bash
# ==============================================================================
# 墨灵 Moling — 飞书机器人通知脚本
# ==============================================================================
# 用途: 向飞书群发送部署/告警/健康状态通知
#
# 前置条件:
#   1. 飞书群 → 设置 → 群机器人 → 添加自定义机器人 → 复制 webhook URL
#   2. 配置环境变量: export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
#   3. 可选签名校验: export FEISHU_SECRET="your-secret"
#
# 用法:
#   bash feishu-notify.sh deploy-start   "v20240620-abc1234" "production"
#   bash feishu-notify.sh deploy-success "v20240620-abc1234" "http://124.222.163.79:8080/moling"
#   bash feishu-notify.sh deploy-fail    "v20240620-abc1234" "数据库迁移失败"
#   bash feishu-notify.sh health-alert   "后端 API 响应超时" "P0"
#   bash feishu-notify.sh smoke-report   "通过" "4/4"
# ==============================================================================

set -euo pipefail

# ---- 配置 ----
WEBHOOK_URL="${FEISHU_WEBHOOK_URL:-}"
SECRET="${FEISHU_SECRET:-}"
TYPE="${1:-help}"
PARAM1="${2:-}"
PARAM2="${3:-}"
PARAM3="${4:-}"

# ---- 颜色 ----
COLOR_RED="red"
COLOR_GREEN="green"
COLOR_YELLOW="yellow"
COLOR_BLUE="blue"

# ---- 飞书消息卡片模板 ----

# 部署开始
card_deploy_start() {
    local version="$1" env="$2"
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "🚀 墨灵部署开始"},
            "template": "${COLOR_BLUE}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**版本**: ${version}\n**环境**: ${env}\n**触发**: GitHub Actions\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')"}
            },
            {
                "tag": "hr"
            },
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": "流水线运行中..."}]
            }
        ]
    }
}
JSON
}

# 部署成功
card_deploy_success() {
    local version="$1" url="$2"
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "✅ 墨灵部署成功"},
            "template": "${COLOR_GREEN}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**版本**: ${version}\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')\n**访问**: [${url}](${url})"}
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开墨灵"},
                        "type": "primary",
                        "url": "${url}"
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看 Actions"},
                        "type": "default",
                        "url": "https://github.com/2eho/moling/actions"
                    }
                ]
            }
        ]
    }
}
JSON
}

# 部署失败
card_deploy_fail() {
    local version="$1" reason="$2"
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "❌ 墨灵部署失败"},
            "template": "${COLOR_RED}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**版本**: ${version}\n**原因**: ${reason}\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')\n\n⚠️ 已触发自动回滚，请检查 Actions 日志"}
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看日志"},
                        "type": "danger",
                        "url": "https://github.com/2eho/moling/actions"
                    }
                ]
            }
        ]
    }
}
JSON
}

# 冒烟测试报告
card_smoke_report() {
    local result="$1" score="$2"
    local color="${COLOR_GREEN}"
    local emoji="✅"
    if [ "$result" != "通过" ]; then
        color="${COLOR_RED}"
        emoji="❌"
    fi
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "${emoji} 墨灵冒烟测试 — ${result}"},
            "template": "${color}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**结果**: ${result}\n**通过率**: ${score}\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')"}
            }
        ]
    }
}
JSON
}

# 健康告警
card_health_alert() {
    local detail="$1" severity="$2"
    local color="${COLOR_RED}"
    local emoji="🚨"
    if [ "$severity" = "P1" ]; then
        color="${COLOR_YELLOW}"
        emoji="⚠️"
    fi
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "${emoji} 墨灵健康告警 [${severity}]"},
            "template": "${color}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**详情**: ${detail}\n**级别**: ${severity}\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')\n\n请立即检查服务状态"}
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "Grafana 查看"},
                        "type": "danger",
                        "url": "http://124.222.163.79:3001"
                    }
                ]
            }
        ]
    }
}
JSON
}

# 自动回滚通知
card_rollback() {
    local version="$1" prev_version="$2"
    cat << JSON
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "🔄 墨灵自动回滚"},
            "template": "${COLOR_YELLOW}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**回滚版本**: ${version} → ${prev_version}\n**原因**: 部署后健康检查失败\n**时间**: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')\n\n服务已恢复到上一版本，请排查问题"}
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看日志"},
                        "type": "default",
                        "url": "https://github.com/2eho/moling/actions"
                    }
                ]
            }
        ]
    }
}
JSON
}

# ---- 发送到飞书 ----
send() {
    if [ -z "$WEBHOOK_URL" ]; then
        echo "❌ 未配置 FEISHU_WEBHOOK_URL，跳过飞书通知"
        return 0
    fi

    # 签名校验（可选）
    if [ -n "$SECRET" ]; then
        local timestamp=$(date +%s)
        local sign=$(echo -n "${timestamp}\n${SECRET}" | openssl dgst -sha256 -binary | base64)
        WEBHOOK_URL="${WEBHOOK_URL}&timestamp=${timestamp}&sign=${sign}"
    fi

    local payload="$1"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        echo "✅ 飞书通知发送成功"
    else
        echo "⚠️  飞书通知发送失败 (HTTP ${http_code})"
    fi
}

# ---- 主路由 ----
case "$TYPE" in
    deploy-start)
        send "$(card_deploy_start "$PARAM1" "$PARAM2")"
        ;;
    deploy-success)
        send "$(card_deploy_success "$PARAM1" "$PARAM2")"
        ;;
    deploy-fail)
        send "$(card_deploy_fail "$PARAM1" "$PARAM2")"
        ;;
    smoke-report)
        send "$(card_smoke_report "$PARAM1" "$PARAM2")"
        ;;
    health-alert)
        send "$(card_health_alert "$PARAM1" "${PARAM2:-P1}")"
        ;;
    rollback)
        send "$(card_rollback "$PARAM1" "$PARAM2")"
        ;;
    test)
        # 测试飞书连接
        send '{"msg_type":"text","content":{"text":"🧪 墨灵飞书机器人测试消息 — 连接正常"}}'
        ;;
    help|*)
        echo "用法: $0 <type> [args...]"
        echo ""
        echo "通知类型:"
        echo "  deploy-start   <version> <env>        部署开始"
        echo "  deploy-success <version> <url>         部署成功"
        echo "  deploy-fail    <version> <reason>      部署失败"
        echo "  smoke-report   <result>  <score>       冒烟测试报告"
        echo "  health-alert   <detail>  <severity>    健康告警 (P0/P1)"
        echo "  rollback       <version> <prev_version> 回滚通知"
        echo "  test                                    测试飞书连接"
        echo ""
        echo "配置: export FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'"
        ;;
esac
