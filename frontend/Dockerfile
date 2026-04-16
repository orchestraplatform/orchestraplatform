# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy build files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration and runtime entrypoint
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Allow the nginx user to write config.js at startup
RUN chmod +x /docker-entrypoint.sh \
    && chown -R nginx:nginx /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
