// User router for user profile and settings
import { z } from "zod";
import { router, demoProcedure } from "../trpc";

export const userRouter = router({
  // Get current user profile
  getProfile: demoProcedure.query(async ({ ctx }) => {
    return {
      id: ctx.user?.id || "demo-user",
      email: ctx.user?.email || "demo@example.com",
      name: "Demo User",
      image: null,
      createdAt: new Date().toISOString(),
    };
  }),

  // Update user profile
  updateProfile: demoProcedure
    .input(
      z.object({
        name: z.string().min(1).max(100).optional(),
        image: z.string().url().nullable().optional(),
      })
    )
    .mutation(async ({ input }) => {
      return {
        id: "demo-user",
        email: "demo@example.com",
        name: input.name || "Demo User",
        image: input.image,
        updatedAt: new Date().toISOString(),
      };
    }),

  // Get user settings
  getSettings: demoProcedure.query(async () => {
    return {
      theme: "dark",
      notifications: {
        email: true,
        push: true,
        approvalReminders: true,
      },
      hitlSettings: {
        autoExecuteInternal: true,
        requireApprovalOutbound: true,
        confidenceThreshold: 0.85,
      },
    };
  }),

  // Update user settings
  updateSettings: demoProcedure
    .input(
      z.object({
        theme: z.enum(["light", "dark"]).optional(),
        notifications: z
          .object({
            email: z.boolean().optional(),
            push: z.boolean().optional(),
            approvalReminders: z.boolean().optional(),
          })
          .optional(),
        hitlSettings: z
          .object({
            autoExecuteInternal: z.boolean().optional(),
            requireApprovalOutbound: z.boolean().optional(),
            confidenceThreshold: z.number().min(0).max(1).optional(),
          })
          .optional(),
      })
    )
    .mutation(async ({ input }) => {
      return {
        success: true,
        settings: input,
        updatedAt: new Date().toISOString(),
      };
    }),
});
