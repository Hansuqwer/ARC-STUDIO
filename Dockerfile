FROM node:18-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/arc-extension/package.json packages/arc-extension/
COPY packages/arc-browser-app/package.json packages/arc-browser-app/

# Install dependencies
RUN pnpm install --frozen-lockfile --prod

# Copy source
COPY . .

# Build
RUN cd packages/arc-extension && pnpm build
RUN cd packages/arc-browser-app && NODE_ENV=production pnpm build:prod

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start
CMD ["pnpm", "start:prod"]
