# FarmApp Frontend — Multi-stage Docker build
# Stage 1: Build the React app with Vite
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.30-alpine

# Pick up Alpine security fixes released after the base image was built
RUN apk upgrade --no-cache

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Writes /config.js from API_BASE_URL at container start (runtime config)
COPY docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod 755 /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 80

# Runs as root for now (accepted until the nginx-unprivileged switch, see DS-0002
# in .trivyignore.yaml)
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["nginx", "-g", "daemon off;"]
