# Nginx ka lightweight alpine image use karenge
FROM nginx:alpine

# Nginx ke default public folder mein apna frontend code copy karenge
COPY . /usr/share/nginx/html

# Nginx default port 80 par chalta hai
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]