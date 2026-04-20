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

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
