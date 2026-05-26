# Build stage
FROM oven/bun:1.2-alpine AS builder

WORKDIR /app

COPY apps/frontend/package.json apps/frontend/bun.lock* ./
COPY bun.lock ./

RUN bun install

COPY apps/frontend .

RUN bun run build

# Production stage
FROM oven/bun:1.2-alpine

WORKDIR /app

# Install serve to run the built app
RUN bun install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
