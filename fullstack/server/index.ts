// Main server entry point - Hono + tRPC + JWT Auth
import { Hono } from "hono";
import { cors } from "hono/cors";
import { trpcServer } from "@hono/trpc-server";
import { authApp, verifyToken, type UserPayload } from "./auth";
import { appRouter } from "./router";
import { createContext } from "./context";
import { serve } from "@hono/node-server";

const app = new Hono();

// Context variables type
type Variables = {
  user: UserPayload | null;
};

app.use("*", cors<{ Variables: Variables }>({
  origin: ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
  credentials: true,
}));

// Health check
app.get("/health", (c) => {
  return c.json({
    status: "ok",
    version: "0.1.0",
    service: "echoteam-api",
  });
});

// JWT Auth routes - mount at /api/auth/*
app.route("/", authApp);

// tRPC endpoint
app.use(
  "/trpc/*",
  trpcServer({
    router: appRouter,
    createContext: async (opts) => {
      // @hono/trpc-server passes headers directly in opts
      const authHeader = opts.event?.req?.headers?.get?.("authorization") ||
                         opts.event?.req?.headers?.authorization ||
                         opts.headers?.get?.("authorization") ||
                         opts.headers?.authorization;
      let user = null;

      if (authHeader?.startsWith("Bearer ")) {
        const token = authHeader.slice(7);
        user = verifyToken(token);
      }

      return {
        user,
      };
    },
  })
);

// REST API endpoints (for external integrations)
const api = new Hono<{ Variables: Variables }>();

api.get("/clones", (c) => {
  return c.json({
    clones: [
      { id: "1", type: "CALENDAR", name: "Calendar Clone", enabled: true },
      { id: "2", type: "EMAIL", name: "Email Clone", enabled: true },
      { id: "3", type: "OPS", name: "Ops Clone", enabled: true },
    ],
  });
});

api.get("/actions/pending", (c) => {
  return c.json({
    actions: [
      {
        id: "action_1",
        type: "draft",
        cloneType: "EMAIL",
        status: "PENDING",
        confidence: 0.85,
        requiresApproval: true,
        payload: { to: "user@example.com" },
      },
      {
        id: "action_2",
        type: "schedule",
        cloneType: "CALENDAR",
        status: "PENDING",
        confidence: 0.92,
        requiresApproval: false,
        payload: { event: "Team meeting" },
      },
    ],
  });
});

api.get("/stats", (c) => {
  return c.json({
    pending: 2,
    approved: 5,
    executed: 12,
    autoExecuted: 3,
  });
});

// AI Service proxy endpoints
api.all("/ai/**", async (c) => {
  const aiServiceUrl = process.env.AI_SERVICE_URL || "http://localhost:8000";
  const path = c.req.path.replace("/api/ai", "");
  const url = `${aiServiceUrl}${path}`;
  const method = c.req.method;
  const body = ["GET", "HEAD"].includes(method) ? undefined : await c.req.text();
  const headers = Object.fromEntries(c.req.headers.entries());

  try {
    const response = await fetch(url, {
      method,
      headers,
      body,
    });
    const data = await response.json();
    return c.json(data, response.status);
  } catch (error) {
    return c.json({ error: "AI service unavailable" }, 503);
  }
});

app.route("/api", api);

// Start server
const PORT = process.env.PORT || 3001;

console.log(`Starting EchoTeam API server on port ${PORT}...`);
console.log(`Auth: http://localhost:${PORT}/api/auth`);
console.log(`tRPC: http://localhost:${PORT}/trpc`);

serve({
  fetch: app.fetch,
  port: PORT,
});

console.log(`EchoTeam API running at http://localhost:${PORT}`);
