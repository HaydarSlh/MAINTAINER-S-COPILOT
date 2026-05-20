# Multi-stage: Vite build → nginx static server.
# Serves the React bundle + /widget.js loader with proper cache headers.

FROM node:20-slim AS build
WORKDIR /build
COPY widget/package*.json ./
RUN npm ci
COPY widget/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /build/dist /usr/share/nginx/html
# widget.js loader served at /widget.js (embedded by host pages via <script src>)
COPY widget/public/widget-loader.js /usr/share/nginx/html/widget.js
COPY docker/nginx-widget.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
