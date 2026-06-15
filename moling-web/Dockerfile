# =============================================================================
# Moling Frontend Dockerfile
# =============================================================================
# 多阶段构建（standalone 模式）：
#   1. builder: 安装依赖 + 构建
#   2. runner: 使用 Node.js 运行 next start
# =============================================================================

# ---- Build Stage ----
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# ---- 构建参数（生产环境下必须传入正确的 API 地址）----
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-http://124.222.163.79:8080/moling/api/v1}

# 安装依赖（先装，NODE_ENV 在后面设，确保 devDependencies 被安装）
COPY package.json package-lock.json* ./
RUN npm ci

# 设置环境变量
ENV NODE_ENV=production

# 复制源代码并构建
COPY . .
RUN npm run build

# ---- Runtime Stage ----
FROM node:20-alpine AS runner

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production
ENV PORT=3000

# 从构建阶段复制产物
COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static/

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S frontend -u 1001
USER frontend

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

# 启动 Next.js 服务器（standalone 模式下 server.js 在根目录）
CMD ["node", "server.js"]