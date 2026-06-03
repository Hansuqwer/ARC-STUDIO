FROM node:20-alpine AS build

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/arc-extension/package.json packages/arc-extension/
COPY applications/browser/package.json applications/browser/

# Install dependencies
RUN pnpm install --frozen-lockfile --prod

# Copy source
COPY . .

# Build
RUN cd packages/arc-extension && pnpm build
RUN cd applications/browser && NODE_ENV=production pnpm build:prod

RUN addgroup -S arc && adduser -S arc -G arc
RUN chown -R arc:arc /app
USER arc

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start
CMD ["pnpm", "--filter", "@arc-studio/browser", "start"]
