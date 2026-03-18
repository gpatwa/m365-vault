# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Use relative API path for Docker (nginx proxies /api to backend)
ENV VITE_API_BASE=/api
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# Default backend URL (Docker Compose). Override via env var for cloud deploy.
ENV BACKEND_URL=http://backend:8000
# Only substitute BACKEND_URL — leave nginx variables ($host, $uri, etc.) untouched
ENV NGINX_ENVSUBST_FILTER=BACKEND_URL
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
