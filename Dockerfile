FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY photo.jpg /usr/share/nginx/html/photo.jpg

EXPOSE 80
