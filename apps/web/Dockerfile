FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Bind to all interfaces: the container sits on two Docker networks (compose +
# coolify proxy) and Traefik may connect via either one. Without this, Next.js
# standalone binds to the container-ID hostname (a single interface) and the
# proxy intermittently gets connection refused -> 502.
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]

# --- Agentic Security Firewall: Katman 2 (non-root hardening) ---
RUN [ -d /app ] && chown -R node:node /app || true
USER node
