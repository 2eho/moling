# ==========================================================================
# 墨灵 (Moling) — Build, test, and deployment targets
# ==========================================================================

.PHONY: rust-build rust-test rust-lint rust-clean rust-check-all \
        docker-build docker-up docker-down \
        build test lint clean deploy dev

# ── Rust targets ──────────────────────────────────────────────────────────

RUST_PATH := .

rust-build:
	cd $(RUST_PATH) && cargo build --release

rust-test:
	cd $(RUST_PATH) && cargo test

rust-lint:
	cd $(RUST_PATH) && cargo clippy -- -D warnings

rust-clean:
	cd $(RUST_PATH) && cargo clean

# Check all crates
rust-check-all:
	cd $(RUST_PATH) && cargo check --workspace

# ── Docker targets ────────────────────────────────────────────────────────

DOCKERFILE := docker/Dockerfile
IMAGE_TAG  := moling-server:latest

docker-build:
	docker build -f $(DOCKERFILE) -t $(IMAGE_TAG) .

docker-up:
	docker compose -f docker/docker-compose.prod.yml up -d

docker-down:
	docker compose -f docker/docker-compose.prod.yml down

docker-logs:
	docker compose -f docker/docker-compose.prod.yml logs -f

# ── Combined targets ──────────────────────────────────────────────────────

build: rust-build
	@echo "[OK] Rust release build complete"

test: rust-test
	@echo "[OK] All tests passed"

lint: rust-lint
	@echo "[OK] Clippy checks passed"

clean: rust-clean
	@echo "[OK] Clean complete"

# ── Development ───────────────────────────────────────────────────────────

dev:
	cd $(RUST_PATH) && cargo run -p moling-server

# ── Deploy ────────────────────────────────────────────────────────────────

deploy: rust-build docker-build
	@echo "[OK] Build complete. Run 'make docker-up' to start services."
	docker compose -f docker/docker-compose.prod.yml up -d
