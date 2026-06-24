# ==============================================================================
# Moling Frontend — Vite + React (static SPA served by Nginx)
# ==============================================================================
# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy workspace config
COPY pnpm-workspace.yaml ./
COPY package.json ./
COPY packages/ui/package.json packages/ui/

# Copy moling-web package.json
COPY moling-web/package.json moling-web/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY packages/ui/ packages/ui/
COPY moling-web/ moling-web/

# Build
WORKDIR /app/moling-web
RUN pnpm run build

# ==============================================================================
# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy nginx config
COPY deploy/nginx/moling.conf /etc/nginx/conf.d/default.conf

# Copy static files
COPY --from=builder /app/moling-web/dist /usr/share/nginx/html

# Health check endpoint (nginx serves this static file)
RUN echo "ok" > /usr/share/nginx/html/health

EXPOSE 3000

# Run as non-root nginx user (uid=101, built into nginx:alpine)
USER nginx

CMD ["nginx", "-g", "daemon off;"]
