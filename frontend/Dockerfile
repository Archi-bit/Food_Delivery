FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM alpine:3.21
COPY --from=build /app/dist /build
CMD ["sh", "-c", "cp -a /build/. /site/"]
