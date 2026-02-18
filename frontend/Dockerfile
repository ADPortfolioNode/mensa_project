ARG NODE_VERSION=22.13.1
# Multi-stage build: build inside Node, serve static files with nginx
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app

# Install deps and build
COPY package*.json ./
RUN npm ci --legacy-peer-deps || npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
# Remove default nginx page content, then copy React build output
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/build/ /usr/share/nginx/html/
# Use custom nginx config for API proxy
COPY nginx.conf /etc/nginx/nginx.conf
# Expose the standard HTTP port
EXPOSE 80
CMD ["/bin/sh", "-c", "nginx -g 'daemon off;' -c /etc/nginx/nginx.conf"]
