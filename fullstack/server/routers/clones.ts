// Clone router for managing clone configurations
import { z } from "zod";
import { router, demoProcedure } from "../trpc";

const cloneTypeEnum = z.enum(["CALENDAR", "EMAIL", "OPS"]);

const cloneConfigSchema = z.object({
  autoCreateFocusBlocks: z.boolean().optional(),
  meetingBufferMinutes: z.number().optional(),
  confidenceThreshold: z.number().optional(),
  styleTone: z.string().optional(),
  workspace: z.string().optional(),
});

export const clonesRouter = router({
  // Get all clones for user
  getAll: demoProcedure.query(async () => {
    // Return mock data for now
    return [
      {
        id: "clone_1",
        type: "CALENDAR",
        name: "My Calendar Clone",
        enabled: true,
        config: { autoCreateFocusBlocks: true },
      },
      {
        id: "clone_2",
        type: "EMAIL",
        name: "My Email Clone",
        enabled: true,
        config: { styleTone: "professional" },
      },
      {
        id: "clone_3",
        type: "OPS",
        name: "My Ops Clone",
        enabled: true,
        config: { workspace: "notion" },
      },
    ];
  }),

  // Get single clone by ID
  getById: demoProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input }) => {
      return {
        id: input.id,
        type: "CALENDAR",
        name: "My Calendar Clone",
        enabled: true,
        config: { autoCreateFocusBlocks: true },
      };
    }),

  // Create new clone
  create: demoProcedure
    .input(
      z.object({
        type: cloneTypeEnum,
        name: z.string().min(1).max(100),
        config: cloneConfigSchema.optional(),
      })
    )
    .mutation(async ({ input }) => {
      return {
        id: `clone_${Date.now()}`,
        type: input.type,
        name: input.name,
        enabled: true,
        config: input.config || {},
      };
    }),

  // Update clone
  update: demoProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).max(100).optional(),
        enabled: z.boolean().optional(),
        config: cloneConfigSchema.optional(),
      })
    )
    .mutation(async ({ input }) => {
      return {
        id: input.id,
        type: "CALENDAR",
        name: input.name || "Updated Clone",
        enabled: input.enabled ?? true,
        config: input.config || {},
      };
    }),

  // Delete clone
  delete: demoProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input }) => {
      return { success: true, id: input.id };
    }),

  // Toggle clone enabled status
  toggle: demoProcedure
    .input(z.object({ id: z.string(), enabled: z.boolean() }))
    .mutation(async ({ input }) => {
      return { success: true, id: input.id, enabled: input.enabled };
    }),
});
