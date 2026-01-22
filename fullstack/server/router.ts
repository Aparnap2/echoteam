// Main router - combines all sub-routers
import { router } from "./trpc";
import { clonesRouter } from "./routers/clones";
import { actionsRouter } from "./routers/actions";
import { userRouter } from "./routers/user";

export const appRouter = router({
  clones: clonesRouter,
  actions: actionsRouter,
  user: userRouter,
});

// Export type router type signature
export type AppRouter = typeof appRouter;
