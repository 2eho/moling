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

# 安装依赖（需要 devDependencies 来构建 Next.js）
COPY package.json package-lock.json* ./
RUN npm ci

# 复制源代码并构建（静态导出）
COPY . .
RUN npm run build

# 验证构建产物是否存在（next.config.ts 配置了 output: 'export' -> out/ 目录）
RUN ls -la out/ || (echo "ERROR: out/ directory not found. Did you set output: 'export' in next.config.ts?" && exit 1)

# ---- Runtime Stage ----
FROM nginx:alpine AS runner

# 安装必要的工具
RUN apk add --no-cache curl wget

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S frontend -u 1001

# 复制 Nginx 配置文件
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制静态文件（next export 输出到 out/）
COPY --from=builder /app/out /usr/share/nginx/html

# 设置文件权限
RUN chown -R frontend:nodejs /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# 验证静态文件存在
RUN ls -la /usr/share/nginx/html/

# 切换为非 root 用户
USER frontend

# 暴露端口
EXPOSE 80

# 健康检查（Nginx 静态文件服务）
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
