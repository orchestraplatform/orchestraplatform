import { WorkshopPhase } from '../api/generated';
import type { WorkshopInstanceResponse } from '../api/generated';

export const ACTIVE_PHASES = new Set<WorkshopPhase>([
  WorkshopPhase.PENDING,
  WorkshopPhase.CREATING,
  WorkshopPhase.STARTING,
  WorkshopPhase.READY,
  WorkshopPhase.RUNNING,
]);

// Admins get every user's instances from /instances/ (server/api/routes/instances.py
// owner_filter=None for admins), so this must be scoped to the signed-in user or an
// admin's template card would offer "Connect" into someone else's session. If the
// current user hasn't loaded yet, include nothing — cards fall back to Launch.
export function buildActiveByTemplate(
  items: WorkshopInstanceResponse[],
  currentUserEmail: string | undefined
): Map<string, WorkshopInstanceResponse> {
  const map = new Map<string, WorkshopInstanceResponse>();
  if (!currentUserEmail) return map;
  for (const inst of items) {
    if (ACTIVE_PHASES.has(inst.phase) && inst.ownerEmail === currentUserEmail) {
      map.set(inst.workshopId, inst);
    }
  }
  return map;
}
