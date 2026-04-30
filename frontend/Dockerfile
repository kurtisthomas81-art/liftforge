FROM node:18-alpine AS builder

WORKDIR /app

RUN apk add --no-cache python3

COPY package.json .
RUN npm install

COPY . .
RUN python3 generate_icons.py
RUN npm run build

# Production image
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
