# =============================================================================
# frontend.Dockerfile — Nginx static file server + API reverse proxy
#
# Builds a container that does two things:
#   1. Serves the HTML / CSS / JS files directly to the browser
#   2. Proxies any request to /api/* → the backend Flask container
#      (configured in nginx.conf — the browser never talks to port 8080 directly)
#
# Build context expected layout:
#   frontend/
#     index.html
#     style.css
#     script.js
#     status-codes.js
#     json2html.min.js
#     nginx.conf
#     frontend.Dockerfile
# =============================================================================

# Use the official Nginx Alpine image as the base.
# Alpine Linux keeps the image tiny (~25 MB) while still providing a full Nginx.
FROM nginx:1.27-alpine

# Remove the default Nginx server configuration that ships with the image.
# If we don't delete it, both configs would load and could conflict.
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom Nginx config into the config directory.
# nginx.conf tells Nginx to:
#   • serve files from /usr/share/nginx/html for all normal routes
#   • forward /api/* requests to http://backend_app:8080/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy all static frontend files into the directory Nginx serves by default.
# These are the files the browser downloads when a user visits the site.
COPY index.html          /usr/share/nginx/html/
COPY style.css           /usr/share/nginx/html/
COPY script.js           /usr/share/nginx/html/
COPY status-codes.js     /usr/share/nginx/html/
COPY json2html.min.js    /usr/share/nginx/html/

# Document that Nginx listens on port 80 inside the container.
# Actual host port mapping is in docker-compose.yml (ports: "80:80").
EXPOSE 80

# No CMD needed — the official Nginx image already defines the default command
# (nginx -g "daemon off;") which keeps Nginx running in the foreground.
