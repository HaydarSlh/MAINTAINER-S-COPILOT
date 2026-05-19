# Image for the `widget` service: builds the React bundle (Vite) and serves
# the bundle + /widget.js loader as static files with proper cache headers.
# Multi-stage: node build -> static server.

# TODO stage 1: node:20 -> npm ci && npm run build (widget/)
# TODO stage 2: static server (nginx/caddy) serving widget/dist + widget-loader/
FROM node:20-slim AS build
WORKDIR /build
# COPY widget/ ./ ; RUN npm ci && npm run build

FROM nginx:alpine
# COPY --from=build /build/dist /usr/share/nginx/html
# COPY widget-loader/widget.js /usr/share/nginx/html/widget.js
