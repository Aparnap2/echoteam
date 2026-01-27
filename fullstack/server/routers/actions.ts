// Action router for HITL (Human-in-the-Loop) management
import { z } from "zod";
import { router, demoProcedure } from "../trpc";

const actionStatusEnum = z.enum([
  "PENDING",
  "APPROVED",
  "REJECTED",
  "EXECUTED",
  "FAILED",
]);

export const actionsRouter = router({
  // Get all actions for user (with filtering)
  getAll: demoProcedure
    .input(
      z.object({
        status: actionStatusEnum.optional(),
        cloneType: z.string().optional(),
        limit: z.number().min(1).max(100).default(50),
        offset: z.number().min(0).default(0),
      }).optional()
    )
    .query(async () => {
      // Mock data for now
      return {
        actions: [
          {
            id: "action_1",
            type: "create_focus_block",
            status: "PENDING",
            cloneType: "CALENDAR",
            confidence: 0.92,
            requiresApproval: false,
            payload: { duration: 60 },
            createdAt: new Date().toISOString(),
          },
          {
            id: "action_2",
            type: "draft",
            status: "PENDING",
            cloneType: "EMAIL",
            confidence: 0.85,
            requiresApproval: true,
            payload: { to: "user@example.com" },
            createdAt: new Date().toISOString(),
          },
        ],
        total: 2,
      };
    }),

  // Get pending actions (approval queue)
  getPending: demoProcedure.query(async () => {
    return [
      {
        id: "action_pending_1",
        type: "draft",
        status: "PENDING",
        cloneType: "EMAIL",
        confidence: 0.85,
        requiresApproval: true,
        payload: { to: "user@example.com", subject: "Re: Meeting" },
        createdAt: new Date().toISOString(),
      },
    ];
  }),

  // Get action by ID
  getById: demoProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input }) => {
      return {
        id: input.id,
        type: "draft",
        status: "PENDING",
        cloneType: "EMAIL",
        confidence: 0.85,
        requiresApproval: true,
        payload: { to: "user@example.com" },
        result: null,
        createdAt: new Date().toISOString(),
      };
    }),

  // Approve action
  approve: demoProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input }) => {
      return {
        id: input.id,
        status: "APPROVED",
        approvedAt: new Date().toISOString(),
      };
    }),

  // Reject action
  reject: demoProcedure
    .input(z.object({ id: z.string(), reason: z.string().optional() }))
    .mutation(async ({ input }) => {
      return {
        id: input.id,
        status: "REJECTED",
        reason: input.reason,
        rejectedAt: new Date().toISOString(),
      };
    }),

  // Get action statistics
  getStats: demoProcedure.query(async () => {
    return {
      pending: 5,
      approved: 12,
      rejected: 2,
      executed: 45,
      autoExecuted: 30,
    };
  }),
});
