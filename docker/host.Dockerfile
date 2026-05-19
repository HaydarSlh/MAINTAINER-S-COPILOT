# Image for the `host` service: nginx serving the demo host page that embeds
# the widget. Distinct origin from `widget` so the allowlist demo is real.

FROM nginx:alpine
COPY demo/host/nginx.conf /etc/nginx/conf.d/default.conf
COPY demo/host/index.html /usr/share/nginx/html/index.html
