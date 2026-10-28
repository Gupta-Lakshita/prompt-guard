# Prompt Guard frontend — static build served by nginx.
#
# VITE_API_BASE_URL is baked in at BUILD time (Vite env vars are compiled
# into the bundle, not read at container runtime), so pass it as a build arg:
#   docker build -f frontend/Dockerfile --build-arg VITE_API_BASE_URL=https://your-backend.example -t prompt-guard-frontend frontend/
#   docker run -p 8080:80 prompt-guard-frontend

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA fallback so client-side routing (react-router) works on refresh.
RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; try_files $uri /index.html; } }' \
    > /etc/nginx/conf.d/default.conf
EXPOSE 80
