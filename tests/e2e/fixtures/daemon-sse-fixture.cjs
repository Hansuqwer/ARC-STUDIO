const http = require('http');

const host = process.env.ARC_E2E_DAEMON_HOST || '127.0.0.1';
const port = Number(process.env.ARC_E2E_DAEMON_PORT || '32173');

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${host}:${port}`);
  const runMatch = url.pathname.match(/^\/api\/runs\/([^/]+)\/events$/);

  if (url.pathname === '/') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, service: 'arc-e2e-daemon-sse-fixture' }));
    return;
  }

  if (!runMatch || url.searchParams.get('mode') !== 'live') {
    res.writeHead(404, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
    return;
  }

  const runId = decodeURIComponent(runMatch[1]);

  res.writeHead(200, {
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache, no-transform',
    connection: 'keep-alive',
    'x-accel-buffering': 'no',
  });

  res.write(`event: arc\n`);
  res.write(`data: ${JSON.stringify({ type: 'RUN_STARTED', run_id: runId, timestamp: '2026-01-01T00:00:00.000Z', sequence: 0, source: 'e2e-fixture' })}\n\n`);

  setTimeout(() => {
    res.write(`event: arc\n`);
    res.write(
      `data: ${JSON.stringify({ type: 'RUN_COMPLETED', run_id: runId, timestamp: '2026-01-01T00:00:01.000Z', sequence: 1, status: 'completed', source: 'e2e-fixture' })}\n\n`,
    );
    res.end();
  }, 25);
});

server.listen(port, host, () => {
  process.stdout.write(`ARC e2e daemon SSE fixture listening on http://${host}:${port}\n`);
});

process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});
