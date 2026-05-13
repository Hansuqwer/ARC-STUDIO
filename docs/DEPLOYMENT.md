# Deployment Guide

## Production Build

```bash
# Build extension first (copies CSS assets)
cd packages/arc-extension && pnpm build

# Build browser app in production mode
cd packages/arc-browser-app
NODE_ENV=production pnpm build:prod
```

## Expected Bundle Sizes

| Artifact | Size |
|----------|------|
| Total lib/ | ~38 MB |
| Frontend | ~26 MB |
| bundle.js (main) | ~11 MB |
| secondary-window.js | ~9.8 MB |
| Backend | ~11 MB |

Development build is ~521 MB (includes source maps and stats.json).

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `NODE_ENV` | Build mode (`production`/`development`) | `development` |
| `ARC_SWARMGRAPH_CLI` | Path to SwarmGraph CLI binary | - |
| `ARC_TRUST_WORKSPACE_LAUNCHER` | Trust workspace launcher path | - |
| `THEIA_HOST` | Hostname for Theia server | `0.0.0.0` |
| `THEIA_PORT` | Port for Theia server | `3000` |

## Starting the Application

```bash
# Production start
cd packages/arc-browser-app
NODE_ENV=production pnpm start:prod

# Or manually
NODE_ENV=production npx theia start --hostname=0.0.0.0 --port=3000 /path/to/workspace
```

## Security Checklist

- [ ] **Gateway Token**: Set `THEIA_GATEWAY_TOKEN` or configure authentication
- [ ] **HTTPS**: Use reverse proxy (nginx/caddy) for TLS termination
- [ ] **Authentication**: Configure Theia auth plugin or external auth proxy
- [ ] **Rate Limiting**: Add rate limiting at reverse proxy level
- [ ] **CORS**: Restrict CORS origins to known domains
- [ ] **Workspace Isolation**: Run each user in separate container/process
- [ ] **File System Access**: Restrict accessible paths via workspace config
- [ ] **Environment Variables**: Never expose secrets in frontend bundle
- [ ] **Dependencies**: Run `pnpm audit` before deployment

## Reverse Proxy Example (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name arc.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Rate limiting
    limit_req zone=arc burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Content-Security-Policy "default-src 'self'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: blob:;" always;
    }
}
```

## Docker Deployment

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
RUN cd packages/arc-extension && pnpm build
RUN cd packages/arc-browser-app && NODE_ENV=production pnpm build:prod

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/packages/arc-browser-app/lib ./lib
COPY --from=builder /app/packages/arc-browser-app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "./lib/backend/main.js", "--hostname=0.0.0.0", "--port=3000"]
```

## Monitoring

- Monitor memory usage (Theia typically uses 200-500 MB per instance)
- Set up health check endpoint
- Log aggregation for error tracking
- Monitor WebSocket connection stability
