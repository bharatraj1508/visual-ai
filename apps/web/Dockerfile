# syntax=docker/dockerfile:1
# Next.js (App Router) web app. Built from the REPO ROOT as context so the yarn
# workspace + lockfile resolve exactly like local dev. Produces a lean
# standalone runtime image (see `output: "standalone"` in next.config.mjs).

# ---- builder: install workspace deps, then build ----------------------------
FROM node:22-alpine AS builder
WORKDIR /app

# Copy only the manifests first so `yarn install` is cached until deps change.
COPY package.json yarn.lock ./
COPY apps/web/package.json apps/web/package.json
COPY apps/api/package.json apps/api/package.json
RUN yarn install --frozen-lockfile

# Now the source. node_modules is excluded via .dockerignore, so the installed
# workspace deps above are preserved.
COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so they
# must be present now (not at container start). Compose passes these as build
# args, sourced from the root .env.
ARG NEXT_PUBLIC_BASE_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_MAX_UPLOAD_MB=50
ARG NEXT_PUBLIC_USD_TO_INR=88
ENV NEXT_PUBLIC_BASE_API_URL=$NEXT_PUBLIC_BASE_API_URL \
    NEXT_PUBLIC_MAX_UPLOAD_MB=$NEXT_PUBLIC_MAX_UPLOAD_MB \
    NEXT_PUBLIC_USD_TO_INR=$NEXT_PUBLIC_USD_TO_INR \
    NEXT_TELEMETRY_DISABLED=1

RUN yarn workspace @visual-ai/web build

# ---- runner: minimal image with just the standalone server ------------------
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Run as an unprivileged user.
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Standalone traces the monorepo root (outputFileTracingRoot), so the tree is
# rooted under apps/web/ inside the standalone folder.
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
