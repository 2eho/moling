# ==============================================================================
# Moling Frontend Dockerfile
# ==============================================================================
# 多阶段构建：
#   1. builder: 安装依赖 + 构建静态文件
#   2. runner: 使用 Nginx 提供静态文件 + 反向代理 API
# ==============================================================================

# ---- Build Stage ----
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production

# 安装依赖（利用 Docker 缓存）
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# 复制源代码并构建
COPY . .
RUN npm run build

# 验证构建产物是否存在
RUN ls -la out/ || ls -la .next/ || echo "Warning: No build output found"

# ---- Runtime Stage ----
FROM nginx:alpine AS runner

# 安装必要的工具
RUN apk add --no-cache curl wget

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S frontend -u 1001

# 复制 Nginx 配置文件
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制静态文件
COPY --from=builder /app/out /usr/share/nginx/html
# 如果是 Next.js 的 .next 构建，使用以下行 instead:
# COPY --from=builder /app/.next /usr/share/nginx/html/.next
# COPY --from=builder /app/public /usr/share/nginx/html/public
# COPY --from=builder /app/package.json /usr/share/nginx/html/

# 设置文件权限
RUN chown -R frontend:nodejs /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# 验证静态文件存在
RUN ls -la /usr/share/nginx/html/

# 切换为非 root 用户
USER frontend

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
