# Build stage
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./
COPY patches ./patches

# Install pnpm and dependencies
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build arguments
ARG VITE_API_URL=http://localhost:8000/api
ARG VITE_APP_TITLE=Analytics Dashboard
ARG VITE_APP_LOGO=/vtx_logo2.png

# Set environment variables for build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_APP_TITLE=${VITE_APP_TITLE}
ENV VITE_APP_LOGO=${VITE_APP_LOGO}

# Build the application
RUN pnpm exec vite build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration (external file for easier maintenance)
# In production, this can be overridden via docker-compose volume mount
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Run nginx as the unprivileged 'nginx' user (uid 101 in nginx:alpine).
# Static-file serving never needs root. Listen on 8080 (unprivileged) instead
# of 80 because the nginx user cannot bind to ports < 1024 without
# CAP_NET_BIND_SERVICE; docker-compose.yml maps host FRONTEND_PORT -> 8080.
# /var/run/nginx.pid is created and chowned so nginx can write the pid file;
# /var/cache/nginx and /var/log/nginx are chowned so nginx can write client-
# body temp files and logs (in prod, /var/cache/nginx and /var/run are tmpfs
# mounts whose ownership is inherited from the container's USER at start).
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid \
    && sed -i 's/listen 80;/listen 8080;/g' /etc/nginx/conf.d/default.conf

USER nginx

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
