// Simple JWT Authentication for EchoTeam
import { Hono } from "hono";
import { cors } from "hono/cors";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "your-super-secret-jwt-key-change-in-production";

export interface UserPayload {
  userId: string;
  email: string;
  name: string;
  exp?: number;
}

// Generate a simple JWT token
export function generateToken(payload: Omit<UserPayload, "exp">): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: "24h" });
}

// Verify a JWT token
export function verifyToken(token: string): UserPayload | null {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as UserPayload;
    return decoded;
  } catch {
    return null;
  }
}

// Auth routes
export const authApp = new Hono<{ Variables: { user: UserPayload | null } }>();

authApp.use("/*", cors({
  origin: ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
  credentials: true,
}));

// Demo login - in production, validate credentials against DB
authApp.post("/api/auth/login", async (c) => {
  const { email, name } = await c.req.json();

  if (!email) {
    return c.json({ error: "Email required" }, 400);
  }

  const userId = crypto.randomUUID();
  const token = generateToken({ userId, email, name: name || email.split("@")[0] });

  return c.json({
    token,
    user: { id: userId, email, name: name || email.split("@")[0] },
  });
});

// Verify token endpoint
authApp.post("/api/auth/verify", async (c) => {
  const authHeader = c.req.header("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ error: "No token provided" }, 401);
  }

  const token = authHeader.slice(7);
  const user = verifyToken(token);

  if (!user) {
    return c.json({ error: "Invalid token" }, 401);
  }

  return c.json({ valid: true, user });
});

// Logout is client-side only (just delete the token)
authApp.post("/api/auth/logout", (c) => {
  return c.json({ success: true });
});
