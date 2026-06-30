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

# Add non-root user for security (nginx:alpine already has nginx user)
RUN mkdir -p /var/run/nginx /var/cache/nginx /var/log/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/nginx.conf /var/cache/nginx /var/run/nginx /var/log/nginx && \
    chmod -R 755 /usr/share/nginx/html

# Expose the standard HTTP port
EXPOSE 80

# Health check — fast interval so verification script catches it quickly
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=2 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

USER nginx
CMD ["nginx", "-g", "daemon off;"]
