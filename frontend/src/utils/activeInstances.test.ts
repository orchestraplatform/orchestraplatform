import { describe, expect, it } from 'vitest';
import { buildActiveByTemplate } from './activeInstances';
import { WorkshopPhase } from '../api/generated';
import type { WorkshopInstanceResponse } from '../api/generated';

// Regression test for #120: /instances/ returns ALL users' instances to admins
// (server/api/routes/instances.py owner_filter=None), so the Templates page must
// scope the Launch-vs-Connect decision to the signed-in user's own instances.

function makeInstance(overrides: Partial<WorkshopInstanceResponse>): WorkshopInstanceResponse {
  return {
    k8sName: 'w-1',
    namespace: 'default',
    templateSlug: 'jupyter',
    workshopId: 'template-1',
    ownerEmail: 'owner@example.org',
    phase: WorkshopPhase.RUNNING,
    ...overrides,
  } as WorkshopInstanceResponse;
}

describe('buildActiveByTemplate', () => {
  it('does not surface another user\'s active instance as the activeInstance for a template', () => {
    const otherUsersInstance = makeInstance({ ownerEmail: 'other-user@example.org' });

    const map = buildActiveByTemplate([otherUsersInstance], 'me@example.org');

    expect(map.get('template-1')).toBeUndefined();
  });

  it('includes the signed-in user\'s own active instance', () => {
    const mine = makeInstance({ ownerEmail: 'me@example.org' });

    const map = buildActiveByTemplate([mine], 'me@example.org');

    expect(map.get('template-1')).toBe(mine);
  });

  it('includes nothing when the current user is not loaded yet', () => {
    const mine = makeInstance({ ownerEmail: 'me@example.org' });

    const map = buildActiveByTemplate([mine], undefined);

    expect(map.size).toBe(0);
  });
});
