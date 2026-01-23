// tRPC initialization for EchoTeam
import { initTRPC, TRPCError } from "@trpc/server";
import type { Context } from "./context";
import { ZodError } from "zod";

const t = initTRPC.context<Context>().create({
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

// Export reusable router and procedure helpers
export const router = t.router;
export const publicProcedure = t.procedure;

// Protected procedure - requires authentication
export const protectedProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED" });
  }
  return next({
    ctx: {
      ...ctx,
      user: ctx.user,
    },
  });
});

// Demo procedure - allows unauthenticated access for demo mode only
// In production, this should be disabled or strictly controlled
export const demoProcedure = t.procedure.use(async ({ ctx, next }) => {
  // Check if demo mode is enabled (use Vite env vars)
  const demoMode = import.meta.env?.DEV || import.meta.env?.VITE_DEMO_MODE === "true";

  if (!demoMode && !ctx.user) {
    throw new TRPCError({
      code: "FORBIDDEN",
      message: "Demo mode is disabled. Please authenticate.",
    });
  }

  return next({
    ctx: {
      ...ctx,
      // Provide a demo user for unauthenticated access in demo mode
      user: ctx.user || {
        id: "demo-user",
        email: "demo@example.com",
        name: "Demo User",
      },
    },
  });
});
