FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app

RUN addgroup -g 1001 -S appgroup && adduser -S -u 1001 appuser -G appgroup

COPY --chown=appuser:appgroup --from=builder /app/.next/standalone ./
COPY --chown=appuser:appgroup --from=builder /app/.next/static ./.next/static
COPY --chown=appuser:appgroup --from=builder /app/public ./public

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/ || exit 1

USER appuser

CMD ["node", "server.js"]
