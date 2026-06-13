ARG NODE_VERSION=22.13.1
# Multi-stage build: build inside Node, serve static files with nginx
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app

# Install deps and build
COPY package*.json ./
RUN npm ci --legacy-peer-deps || npm ci
COPY . .
RUN npm run build && test -f /app/build/index.html

FROM nginx:alpine
# Remove default nginx page content, then copy React build output
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/build/ /usr/share/nginx/html/
# Use custom nginx config for API proxy
COPY nginx.conf /etc/nginx/nginx.conf

# Add non-root user for security
RUN addgroup -g 1001 -S nginx && \
    adduser -S -D -H -u 1001 -h /usr/share/nginx/html -s /sbin/nologin -G nginx -g nginx nginx && \
    chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/nginx.conf /var/cache/nginx /var/run /var/log/nginx && \
    chmod -R 755 /usr/share/nginx/html

# Expose the standard HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

USER nginx
CMD ["nginx", "-g", "daemon off;"]
