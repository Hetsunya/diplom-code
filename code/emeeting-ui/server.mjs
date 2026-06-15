import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const port = Number(process.env.PORT || 5173);
const backend = process.env.BACKEND_HTTP || "http://backend:8080";

const app = express();

const apiProxy = createProxyMiddleware({
  target: backend,
  changeOrigin: true,
  pathRewrite: { "^/api": "" },
});

const wsProxy = createProxyMiddleware({
  target: backend,
  changeOrigin: true,
  ws: true,
  // Mic JSON (base64 WebM) stays open a long time; avoid proxy cutting the connection early.
  timeout: 0,
  proxyTimeout: 0,
});

app.use("/api", apiProxy);
app.use("/ws", wsProxy);

const distDir = path.join(__dirname, "dist");
app.use(express.static(distDir));
// Express 5 doesn't accept "*" string pattern here.
app.get(/.*/, (_req, res) => res.sendFile(path.join(distDir, "index.html")));

// Required for WS: forwarding Upgrade to httpxy. app.listen alone often breaks large binary frames over /ws.
const server = http.createServer(app);
server.on("upgrade", wsProxy.upgrade);

server.listen(port, "0.0.0.0", () => {
  console.log(`[ui] listening on :${port}, proxy -> ${backend}`);
});

