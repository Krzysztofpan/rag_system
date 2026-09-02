# syntax=docker/dockerfile:1

FROM node:22-alpine AS development
WORKDIR /app

ARG BACKEND_URL=/api
ARG SUPABASE_URL
ARG SUPABASE_ANON_KEY
ENV BACKEND_URL=$BACKEND_URL \
    SUPABASE_URL=$SUPABASE_URL \
    SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:22-alpine AS builder
WORKDIR /app

ARG BACKEND_URL=/api
ARG SUPABASE_URL
ARG SUPABASE_ANON_KEY
ENV BACKEND_URL=$BACKEND_URL \
    SUPABASE_URL=$SUPABASE_URL \
    SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY index.html vite.config.ts vite-env.d.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY src ./src
COPY components ./components
COPY contexts ./contexts
COPY hooks ./hooks
COPY lib ./lib
COPY types ./types
COPY services ./services
COPY public ./public
RUN npm run build

FROM caddy:2-alpine AS runtime
# wget: compose healthcheck runs inside this image.
RUN apk add --no-cache wget
COPY Caddyfile Caddyfile.prod Caddyfile.app /etc/caddy/
COPY --from=builder /app/dist /usr/share/caddy
EXPOSE 80 443
