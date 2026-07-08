/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopPhase } from './WorkshopPhase';
/**
 * Response schema for a single workshop instance.
 */
export type WorkshopInstanceResponse = {
    id: string;
    workshopId: string;
    /**
     * Display name of the source template (stamped at launch)
     */
    workshopName?: (string | null);
    /**
     * Slug of the source template, stamped at launch.
     */
    templateSlug: string;
    /**
     * Immutable snapshot of the resolved spec this instance launched with (image, port, duration, env, args, resources, storage).
     */
    resolvedSpec?: Record<string, any>;
    k8sName: string;
    namespace: string;
    ownerEmail: string;
    phase: WorkshopPhase;
    url?: (string | null);
    durationRequested: string;
    launchedAt: string;
    expiresAt?: (string | null);
    terminatedAt?: (string | null);
    createdAt: string;
    updatedAt: string;
};

