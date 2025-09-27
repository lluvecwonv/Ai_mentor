FROM nginx:1.25-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf
COPY proxy_params /etc/nginx/proxy_params
COPY custom.css /etc/nginx/custom.css
COPY suppress-warnings.js /etc/nginx/suppress-warnings.js
COPY ai-mentor-cleanup.js /etc/nginx/ai-mentor-cleanup.js

EXPOSE 8080
