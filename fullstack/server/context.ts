// Context for tRPC - handles auth and database access
import type { inferAsyncReturnType } from "@trpc/server";
import type { FetchCreateContextFnOptions } from "@trpc/server/adapters/fetch";

export async function createContext({ req }: FetchCreateContextFnOptions) {
  // In production, validate JWT/session from headers
  const authHeader = req.headers.get("authorization");
  const userId = authHeader?.replace("Bearer ", "") || "demo-user";

  return {
    user: {
      id: userId,
      email: "demo@example.com",
      tenantId: "tenant_default",
    },
  };
}

export type Context = inferAsyncReturnType<typeof createContext>;
