ARG NODE_VERSION
# Build stage
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files
COPY public ./public
COPY src ./src

# Build the app (if applicable)
RUN npm run build

# Production stage
RUN echo "Building final stage with NODE_VERSION"
ARG NODE_VERSION
FROM node:${NODE_VERSION}-slim AS final
WORKDIR /app

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy built app and production dependencies
COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/build ./build

# Fix npm cache permissions and ensure proper ownership
RUN mkdir -p /app/.npm && \
    chown -R appuser:appgroup /app

ENV NODE_ENV=production
ENV NODE_OPTIONS="--max-old-space-size=4096"
USER appuser

EXPOSE 3000
CMD ["npx", "serve", "-s", "build", "-l", "3000"]
