# ==========================================================================
# 墨灵 (Moling) Rust Server — Multi-stage Docker build (cargo-chef)
# ==========================================================================
#
# Stage 1: Chef   — Install cargo-chef and prepare dependency recipe
# Stage 2: Builder — Cook dependencies from recipe, then compile workspace
# Stage 3: Runner  — Minimal Debian runtime image
#
# Build:
#   docker build -f docker/Dockerfile -t moling-server-rs:latest .
#
# Run:
#   docker run -p 8000:8000 \
#     -e MOLING_HOST=0.0.0.0 \
#     -e MOLING_PORT=8000 \
#     -e MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc \
#     moling-server-rs:latest

# ==========================================================================
# Stage 1: Chef — Prepare cargo-chef recipe for dependency caching
# ==========================================================================
FROM rust:1.85-slim-bookworm AS chef

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pkg-config \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure USTC cargo mirror for faster crate downloads inside Docker
RUN mkdir -p /usr/local/cargo && \
    echo '[source.crates-io]' >> /usr/local/cargo/config.toml && \
    echo 'replace-with = "ustc"' >> /usr/local/cargo/config.toml && \
    echo '' >> /usr/local/cargo/config.toml && \
    echo '[source.ustc]' >> /usr/local/cargo/config.toml && \
    echo 'registry = "sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/"' >> /usr/local/cargo/config.toml

RUN cargo install cargo-chef
WORKDIR /app

# Copy workspace manifest and crate manifests for recipe analysis
COPY Cargo.toml Cargo.lock ./
COPY crates/moling-core/Cargo.toml crates/moling-core/
COPY crates/moling-db/Cargo.toml crates/moling-db/
COPY crates/moling-auth/Cargo.toml crates/moling-auth/
COPY crates/moling-api/Cargo.toml crates/moling-api/
COPY crates/moling-services/Cargo.toml crates/moling-services/
COPY crates/moling-llm/Cargo.toml crates/moling-llm/
COPY crates/moling-worker/Cargo.toml crates/moling-worker/
COPY crates/moling-server/Cargo.toml crates/moling-server/

# Create minimal dummy source files to satisfy Cargo workspace parsing
RUN mkdir -p crates/moling-core/src \
    && echo '' > crates/moling-core/src/lib.rs \
    && mkdir -p crates/moling-db/src \
    && echo '' > crates/moling-db/src/lib.rs \
    && mkdir -p crates/moling-auth/src \
    && echo '' > crates/moling-auth/src/lib.rs \
    && mkdir -p crates/moling-api/src \
    && echo '' > crates/moling-api/src/lib.rs \
    && mkdir -p crates/moling-services/src \
    && echo '' > crates/moling-services/src/lib.rs \
    && mkdir -p crates/moling-llm/src \
    && echo '' > crates/moling-llm/src/lib.rs \
    && mkdir -p crates/moling-worker/src \
    && echo '' > crates/moling-worker/src/lib.rs

RUN cargo chef prepare --recipe-path recipe.json

# ==========================================================================
# Stage 2: Builder — Cook deps (cached) then compile workspace
# ==========================================================================
FROM rust:1.85-slim-bookworm AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pkg-config \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=chef /usr/local/cargo/bin/cargo-chef /usr/local/cargo/bin/cargo-chef
COPY --from=chef /app/recipe.json /app/recipe.json

WORKDIR /app

# Cook (build) dependencies — this layer is cached unless Cargo.toml changes
RUN cargo chef cook --release --recipe-path recipe.json

# Copy full source tree
COPY Cargo.toml Cargo.lock ./
COPY crates/ crates/

# Build workspace (release, only moling-server binary needed at runtime)
RUN cargo build --release -p moling-server \
    && cp target/release/moling-server /usr/local/bin/moling-server

# ==========================================================================
# Stage 3: Runner — Minimal Debian runtime image
# ==========================================================================
FROM debian:bookworm-slim

# Install only runtime essentials (curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with uid 1000
RUN useradd -r -u 1000 -d /app -s /sbin/nologin moling

WORKDIR /app

# Copy binary from builder
COPY --from=builder /usr/local/bin/moling-server /usr/local/bin/moling-server

# Copy .env.example for reference
COPY .env.example /app/.env.example

# Database persistence volume
VOLUME ["/data"]

# Expose application port
EXPOSE 8000

# Default environment variables with MOLING_ prefix
ENV MOLING_HOST=0.0.0.0 \
    MOLING_PORT=8000 \
    MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/ || exit 1

# Switch to non-root user
USER moling

# Entrypoint
ENTRYPOINT ["/usr/local/bin/moling-server"]
