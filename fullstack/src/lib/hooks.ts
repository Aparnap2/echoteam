// tRPC hooks for EchoTeam frontend
import { trpc } from "./trpc";

// Clone types
export type CloneType = "CALENDAR" | "EMAIL" | "OPS";

export interface Clone {
  id: string;
  type: CloneType;
  name: string;
  enabled: boolean;
  config?: Record<string, unknown>;
}

export interface Action {
  id: string;
  type: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED" | "FAILED";
  cloneType: CloneType;
  confidence: number;
  requiresApproval: boolean;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface ActionStats {
  pending: number;
  approved: number;
  rejected: number;
  executed: number;
  autoExecuted: number;
}

// Clone hooks
export function useClones() {
  return trpc.clones.getAll.useQuery();
}

export function useClone(id: string) {
  return trpc.clones.getById.useQuery({ id });
}

export function useCreateClone() {
  return trpc.clones.create.useMutation();
}

export function useUpdateClone() {
  return trpc.clones.update.useMutation();
}

export function useDeleteClone() {
  return trpc.clones.delete.useMutation();
}

export function useToggleClone() {
  return trpc.clones.toggle.useMutation();
}

// Action hooks
export function useActions() {
  return trpc.actions.getAll.useQuery();
}

export function usePendingActions() {
  return trpc.actions.getPending.useQuery();
}

export function useAction(id: string) {
  return trpc.actions.getById.useQuery({ id });
}

export function useApproveAction() {
  return trpc.actions.approve.useMutation();
}

export function useRejectAction() {
  return trpc.actions.reject.useMutation();
}

export function useActionStats() {
  return trpc.actions.getStats.useQuery();
}

// User hooks
export function useUserProfile() {
  return trpc.user.getProfile.useQuery();
}

export function useUpdateProfile() {
  return trpc.user.updateProfile.useMutation();
}

export function useUserSettings() {
  return trpc.user.getSettings.useQuery();
}

export function useUpdateSettings() {
  return trpc.user.updateSettings.useMutation();
}
