/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopCondition } from './WorkshopCondition';
import type { WorkshopPhase } from './WorkshopPhase';
/**
 * Workshop status information.
 */
export type WorkshopStatus = {
    phase: WorkshopPhase;
    url?: (string | null);
    createdAt: (string | null);
    expiresAt: (string | null);
    conditions?: Array<WorkshopCondition>;
};

