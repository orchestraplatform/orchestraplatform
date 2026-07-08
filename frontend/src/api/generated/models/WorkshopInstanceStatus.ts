/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopPhase } from './WorkshopPhase';
/**
 * Lightweight status/URL response for a workshop instance.
 */
export type WorkshopInstanceStatus = {
    id: string;
    k8sName: string;
    phase: WorkshopPhase;
    url?: (string | null);
    expiresAt?: (string | null);
};

