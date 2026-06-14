# ==============================================================================
# Moling Backend Dockerfile
# ==============================================================================
# 多阶段构建：
#   1. builder: 安装构建依赖 + 安装 Python 包
#   2. runtime: 运行时镜像（仅包含运行时依赖）
# ==============================================================================

# ---- Build Stage ----
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统构建依赖（SQLite 只需要 gcc/libffi，无需 pg）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制包源码（setuptools build 需要 app/ 目录）
COPY pyproject.toml .
COPY app/ ./app/
# 先设镜像，再更新 pip，最后装依赖（顺序很重要：镜像设错了国内网络会超时）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --upgrade pip && \
    pip install --no-cache-dir .

# ---- Runtime Stage ----
FROM python:3.11-slim AS runtime

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装运行时系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（确保 /api/v1/health 端点存在）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 运行应用
# 使用 uvicorn 启动 FastAPI 应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
